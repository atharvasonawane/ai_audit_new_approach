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
    if "db" not in cfg:
        cfg["db"] = {}

    cfg["db"]["host"] = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
    cfg["db"]["port"] = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
    cfg["db"]["user"] = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv(
        "MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db")
    )
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
    '- "fetch_vue_block": Fetches raw source code of one block from a Vue file.\n'
    "  Requires: file_path (str) and block_type (one of: script, template, style)\n"
    "  IMPORTANT: Always call get_file_database_report FIRST. Never use this tool first.\n"
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

KNOWN_TOOLS = {"get_high_risk_files", "get_file_database_report", "fetch_vue_block"}


# ==========================================
# 3. TOOL EXECUTION
# ==========================================
_session_cache = {}


def clear_cache():
    global _session_cache
    _session_cache = {}
    print("[CACHE] Cleared")


def execute_tool(tool_name: str, args: dict):
    cache_key = f"{tool_name}:{args.get('file_path', '')}"

    if cache_key in _session_cache:
        print(f"[CACHE] Hit for {cache_key}")
        return _session_cache[cache_key]

    if tool_name == "get_high_risk_files":
        result = db_report_loader.load_high_risk_files(DB_CFG)
        _session_cache[cache_key] = result
        return result

    elif tool_name == "get_file_database_report":
        file_path = args.get("file_path", "")
        report = db_report_loader.load_all_issues_for_file(DB_CFG, file_path)

        # Fuzzy fallback: model often gives just filename, not the full Windows path
        if not report:
            matches = db_report_loader.search_files(DB_CFG, file_path)
            if matches:
                exact_path = matches[0]
                report = db_report_loader.load_all_issues_for_file(DB_CFG, exact_path)
                report["_meta"] = (
                    f"Fuzzy match: resolved '{file_path}' -> '{exact_path}'"
                )

        if not report:
            result = {"error": f"File '{file_path}' not found in database."}
            _session_cache[cache_key] = result
            return result

        # --- NEW: THE COUNTING FIX ---
        # Pre-calculate counts so the 3B model doesn't have to count array lengths manually
        if "api_calls" in report:
            report["total_api_calls_count"] = len(report["api_calls"])
        if "file_flags" in report:
            report["total_flags_count"] = len(report["file_flags"])
        if "ui_defects" in report:
            report["total_ui_defects_count"] = len(report["ui_defects"])
        if "accessibility_defects" in report:
            report["total_accessibility_defects_count"] = len(
                report["accessibility_defects"]
            )
        # -----------------------------

        # Trim raw blobs that would blow the context window
        if "ui_extractions" in report:
            del report["ui_extractions"]
        if "vue_file" in report:
            for k in ["file_content", "raw_code", "template", "script"]:
                report["vue_file"].pop(k, None)

        _session_cache[cache_key] = report
        return report

    elif tool_name == "fetch_vue_block":
        file_path = args.get("file_path", "")
        block_type = args.get("block_type", "script")

        if block_type not in ("script", "template", "style"):
            result = {
                "error": "block_type must be exactly one of: script, template, style"
            }
            _session_cache[cache_key] = result
            return result

        # Fuzzy path resolution — same pattern as get_file_database_report
        if not db_report_loader.load_all_issues_for_file(DB_CFG, file_path):
            matches = db_report_loader.search_files(DB_CFG, file_path)
            if matches:
                file_path = matches[0]

        try:
            from task2_audit.extractors.vue_parser import parse_vue_file
        except ImportError as e:
            result = {
                "error": (
                    f"Cannot import vue_parser. "
                    f"Check that 'task2_audit/extractors/vue_parser.py' exists. "
                    f"Original error: {e}"
                )
            }
            _session_cache[cache_key] = result
            return result

        try:
            parsed_result = parse_vue_file(file_path)
        except Exception as e:
            result = {"error": f"vue_parser failed on file '{file_path}': {e}"}
            _session_cache[cache_key] = result
            return result

        block_map = {
            "script": parsed_result.get("script_text", "No script block found"),
            "template": str(parsed_result.get("template_node", "No template found")),
            "style": parsed_result.get("style_text", "No style block found"),
        }

        result = {
            "file_path": file_path,
            "block_type": block_type,
            "content": block_map[block_type],
        }
        _session_cache[cache_key] = result
        return result


# ==========================================
# 4. JSON EXTRACTOR
# Handles all real-world 3B model output patterns:
#   - Compact:   {"name": ...}
#   - Spaced:    { "name": ...}
#   - Fenced:
