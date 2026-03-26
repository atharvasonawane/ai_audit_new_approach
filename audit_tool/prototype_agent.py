import json
import re
import sys
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# ==========================================
# 1. SECURE CONFIGURATION LOADING
# ==========================================
def load_config():
    """Load database credentials securely from .env and project_config.yaml"""
    # Assuming script is run from audit_tool/ or project_root/
    base_dir = Path(__file__).parent
    config_path = base_dir / "config" / "project_config.yaml"
    
    if not config_path.exists():
        # Fallback for different run contexts
        config_path = Path("audit_tool/config/project_config.yaml")
        
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        
    load_dotenv()
    if "db" not in cfg: cfg["db"] = {}
    
    cfg["db"]["host"] = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
    cfg["db"]["port"] = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
    cfg["db"]["user"] = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv("MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db"))
    return cfg

DB_CFG = load_config()

# ==========================================
# IMPORT — prototype_agent.py is one level ABOVE task7/:
# ==========================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from task7 import db_report_loader

# ==========================================
# 2. SYSTEM PROMPT
# Key changes vs previous version:
#   - Opens with "You CANNOT know anything from memory" to kill
#     the root cause of hallucination before it starts.
#   - "ABSOLUTE RULES" block uses NEVER/ALWAYS language that 3B
#     models respond to better than polite suggestions.
#   - Explicitly bans outputting non-tool-call JSON, closing the
#     loophole where the model printed a fake answer as JSON.
# ==========================================
SYSTEM_INSTRUCTIONS = (
    "You are the Code Audit Librarian, an AI assistant analyzing a legacy Vue.js codebase.\n"
    "You have access to a MySQL database. You CANNOT know anything about this codebase from memory.\n"
    "ALL file data, API calls, defects, and flags MUST come from a tool call. Never invent or guess.\n"
    "\n"
    "TOOLS AVAILABLE:\n"
    '- "get_high_risk_files": Returns a list of risky files. Takes no arguments.\n'
    '- "get_file_database_report": Returns API calls, flags, and defects for a specific file. Requires file_path.\n'
    "\n"
    "HOW TO CALL A TOOL - STRICT FORMAT:\n"
    "Output ONLY a single raw JSON object on one line. No extra text. No markdown. No code fences.\n"
    'Example: {"name": "get_file_database_report", "arguments": {"file_path": "RoleMgt.vue"}}\n'
    'Example: {"name": "get_high_risk_files", "arguments": {}}\n'
    "\n"
    "ABSOLUTE RULES - NEVER BREAK THESE:\n"
    "1. NEVER invent, fabricate, or guess file data, API calls, defects, or flags.\n"
    "2. NEVER output a JSON object as your final answer. Final answers must ALWAYS be plain English.\n"
    "3. NEVER answer a question about a file without first calling get_file_database_report.\n"
    "4. NEVER answer a question about risky files without first calling get_high_risk_files.\n"
    "5. NEVER agree with the user if they contradict the database. If the database says 9 API calls, and the user says 8, you MUST politely correct them and stick to the database facts.\n"
    "\n"
    "WORKFLOW:\n"
    "Step 1 - User asks about a file -> output only the JSON tool call, nothing else.\n"
    "Step 2 - You receive a TOOL RESULT -> summarize it clearly in plain English for the user.\n"
    "Step 3 - Greetings or meta questions -> answer in plain English, no tool needed.\n"
)

# Rolling window: keep last 6 turns to stay within the 3B model 8192-token context
MAX_HISTORY_TURNS = 6

KNOWN_TOOLS = {"get_high_risk_files", "get_file_database_report"}


# ==========================================
# 3. TOOL EXECUTION
# ==========================================
def execute_tool(tool_name: str, args: dict):
    if tool_name == "get_high_risk_files":
        return db_report_loader.load_high_risk_files(DB_CFG)

    elif tool_name == "get_file_database_report":
        file_path = args.get("file_path", "")
        report = db_report_loader.load_all_issues_for_file(DB_CFG, file_path)

        # Fuzzy fallback: model often gives just filename, not the full Windows path
        if not report:
            matches = db_report_loader.search_files(DB_CFG, file_path)
            if matches:
                exact_path = matches[0]
                report = db_report_loader.load_all_issues_for_file(DB_CFG, exact_path)
                report["_meta"] = f"Fuzzy match: resolved '{file_path}' -> '{exact_path}'"

        if not report:
            return {"error": f"File '{file_path}' not found in database."}

        # --- NEW: THE COUNTING FIX ---
        # Pre-calculate counts so the 3B model doesn't have to count array lengths manually
        if "api_calls" in report:
            report["total_api_calls_count"] = len(report["api_calls"])
        if "file_flags" in report:
            report["total_flags_count"] = len(report["file_flags"])
        if "ui_defects" in report:
            report["total_ui_defects_count"] = len(report["ui_defects"])
        if "accessibility_defects" in report:
            report["total_accessibility_defects_count"] = len(report["accessibility_defects"])
        # -----------------------------

        # Trim raw blobs that would blow the context window
        if "ui_extractions" in report:
            del report["ui_extractions"]
        if "vue_file" in report:
            for k in ["file_content", "raw_code", "template", "script"]:
                report["vue_file"].pop(k, None)

        return report

    return {"error": f"Unknown tool '{tool_name}'. Available: {sorted(KNOWN_TOOLS)}"}


# ==========================================
# 4. JSON EXTRACTOR
# Handles all real-world 3B model output patterns:
#   - Compact:   {"name": ...}
#   - Spaced:    { "name": ...}
#   - Fenced:    ```json\n{"name": ...}\n```
#   - Prefixed:  "Sure! {"name": ...}"
# Returns the parsed dict ONLY if "name" is a known tool name.
# Returns None for everything else — INCLUDING hallucinated answer JSON.
# ==========================================
def extract_tool_call(text: str):
    # Strip markdown fences first
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None

    if not candidate:
        start = text.find("{")
        if start == -1:
            return None
        depth, end = 0, -1
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            return None
        candidate = text[start:end]

    try:
        parsed = json.loads(candidate)
        # Critical gate: only accept if it's a known tool — rejects hallucinated answer JSON
        if isinstance(parsed, dict) and parsed.get("name") in KNOWN_TOOLS:
            return parsed
    except json.JSONDecodeError:
        pass

    return None


# ==========================================
# 5. HALLUCINATION DETECTOR
# If the model outputs JSON that is NOT a valid tool call, it has
# hallucinated a fake answer. We intercept it and inject a correction.
# ==========================================
def looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("```")


def build_correction_message(ai_text: str) -> str:
    return (
        "ERROR: You output a JSON object as your answer. This is not allowed.\n"
        "You cannot know the contents of this codebase from memory.\n"
        "You MUST call a tool to get real data. Do not repeat the previous JSON.\n"
        "Output ONLY a valid tool call JSON now, nothing else.\n"
        'Example: {"name": "get_file_database_report", "arguments": {"file_path": "RoleMgt.vue"}}'
    )


# ==========================================
# 6. MAIN LOOP
# ==========================================
if __name__ == "__main__":
    print("Initializing Code Audit Librarian...")

    # Fail fast on DB issues so we know immediately if credentials are wrong
    try:
        db_report_loader.get_db_connection(DB_CFG).close()
        print("[OK] Database connection verified.")
    except Exception as e:
        print(f"[FATAL] Cannot connect to database: {e}")
        print("        Check DB_CFG credentials and confirm MySQL is running.")
        sys.exit(1)

    llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=8192)
    system_msg = SystemMessage(content=SYSTEM_INSTRUCTIONS)
    conversation_turns = []

    print("Agent online. Type 'exit' to quit.\n")

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            print("Shutting down.")
            break

        conversation_turns.append(HumanMessage(content=user_input))

        # Trim rolling window BEFORE invoking the model
        if len(conversation_turns) > MAX_HISTORY_TURNS * 2:
            conversation_turns = conversation_turns[-(MAX_HISTORY_TURNS * 2):]

        # MAX_INNER_ITERATIONS includes headroom for 1 hallucination correction attempt
        MAX_INNER_ITERATIONS = 6
        inner_iterations = 0

        while inner_iterations < MAX_INNER_ITERATIONS:
            inner_iterations += 1

            try:
                full_history = [system_msg] + conversation_turns
                response = llm.invoke(full_history)
                ai_text = response.content.strip()
            except Exception as e:
                print(f"\n[LLM Error] Ollama call failed: {e}")
                print("            Is Ollama running? Try: ollama serve")
                break

            # --- PATH A: Valid tool call ---
            tool_call = extract_tool_call(ai_text)
            if tool_call:
                t_name = tool_call.get("name")
                t_args = tool_call.get("arguments", {})
                print(f"\n[DEBUG] Tool call -> {t_name}  args={t_args}")

                conversation_turns.append(AIMessage(content=ai_text))

                try:
                    tool_data = execute_tool(t_name, t_args)
                    print("[DEBUG] Tool returned data. Feeding back to agent...")
                except Exception as e:
                    tool_data = {"error": f"Tool execution failed: {e}"}
                    print(f"[DEBUG] Tool error: {e}")

                observation = (
                    f"TOOL RESULT for '{t_name}':\n"
                    f"{json.dumps(tool_data, indent=2, default=str)}\n\n"
                    "Now summarize the above result clearly for the user in plain English. "
                    "Do NOT output JSON."
                )
                conversation_turns.append(HumanMessage(content=observation))
                continue  # Let model generate natural-language summary

            # --- PATH B: Hallucinated JSON answer ---
            if looks_like_json(ai_text):
                print("\n[DEBUG] Hallucination detected: model output non-tool JSON. Forcing correction...")
                conversation_turns.append(AIMessage(content=ai_text))
                conversation_turns.append(HumanMessage(content=build_correction_message(ai_text)))
                continue  # Give the model one chance to self-correct

            # --- PATH C: Clean natural-language answer ---
            print("\nLibrarian:\n", ai_text)
            conversation_turns.append(AIMessage(content=ai_text))
            break

        else:
            print("\n[Warning] Agent exceeded max iterations. Possible loop - resetting turn.")