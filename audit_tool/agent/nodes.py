import re
import json
import os
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from agent.state import GraphState

# Added imports for Phase 2:
from tools.db_tools import get_high_risk_files, get_file_report, get_summary_stats, get_critical_files, get_files_by_module, get_flag_summary
from tools.code_tools import fetch_vue_block

# Initialize the LLM and System Message locally
MODEL_NAME = os.getenv("AGENT_MODEL", "qwen2.5-coder:3b")
llm = ChatOllama(model=MODEL_NAME, temperature=0.0, num_ctx=8192)


def router_node(state: GraphState) -> GraphState:
    query = state["user_query"].lower()
    print(f"\n{'=' * 50}")
    print(f"🕵️ [ROUTER] Analyzing user query: '{query}'")

    # The dictionary insertion order guarantees the check order: verify -> summary -> file
    patterns = {
        "verify": [
            r"false positive",
            r"verify",
            r"actually (have|contain)",
            r"double.?check",
            r"confirm",
        ],
        "summary": [
            r"list", 
            r"all files", 
            r"overview", 
            r"codebase",
            r"dangerous", 
            r"critical", 
            r"high risk", 
            r"worst",
            r"most issues", 
            r"should avoid", 
            r"risky files",
            r"which files", 
            r"most dangerous", 
            r"give me"
        ],
        "file": [
            r"\.vue\b",
            r"tell me about", 
            r"what about", 
            r"show me",
            r"give me details on", 
            r"explain", 
            r"describe",
            r"how is", 
            r"how risky is"
        ],
    }

    matched_type = "unknown"
    for q_type, pats in patterns.items():
        if any(re.search(p, query) for p in pats):
            matched_type = q_type
            break

    file_match = re.search(r"[\w/\\]+\.vue", state["user_query"], re.IGNORECASE)
    state["matched_file"] = file_match.group(0) if file_match else ""

    if matched_type == "unknown":
        print("⏳ [ROUTER] No regex match. Asking LLM to classify...")
        prompt = f"Classify this query into one exact word: 'summary', 'file', 'verify', or 'unknown'. Query: {state['user_query']}"
        res = llm.invoke([HumanMessage(content=prompt)])
        clean_res = res.content.strip().lower()
        if clean_res in ["summary", "file", "verify"]:
            matched_type = clean_res

    print(f"🎯 [ROUTER] Decided Route: {matched_type.upper()}")
    if state["matched_file"]:
        print(f"📄 [ROUTER] Extracted File: {state['matched_file']}")

    state["query_type"] = matched_type
    return state


def aggregator_node(state: GraphState) -> GraphState:
    print("\n⚙️ [AGGREGATOR] Fetching high risk files...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    res = get_high_risk_files.invoke({})
    labeled_result = f"DATABASE REPORT - THE FOLLOWING FILES ARE FLAGGED AS HIGH RISK/DANGEROUS:\n{res}"
    state["tool_results"].append(labeled_result)
    return state


def deep_dive_node(state: GraphState) -> GraphState:
    print(f"\n⚙️ [DEEP DIVE] Fetching DB report for {state['matched_file']}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    mf = state["matched_file"]
    
    # If matched_file is empty or missing the .vue extension
    if not mf or not mf.lower().endswith(".vue"):
        print("⏳ [DEEP DIVE] File name missing. Extracting search term from query...")
        
        query_lower = state["user_query"].lower()
        stop_words = [
            "tell", "me", "about", "what", "show", "give", 
            "details", "on", "explain", "describe", "file", 
            "the", "a", "an", "is", "how", "risky", "for", 
            "of", "please", "can", "you"
        ]
        
        # Extract words, filtering out the common stop words
        words = re.findall(r'\b\w+\b', query_lower)
        filtered_words = [w for w in words if w not in stop_words]
        mf = " ".join(filtered_words)
        
        print(f"📄 [DEEP DIVE] Extracted search term: '{mf}'")

    state["matched_file"] = mf
    res_db = get_file_report.invoke({"file_name": state["matched_file"]})
    state["tool_results"].append(str(res_db))
    return state


def validator_node(state: GraphState) -> GraphState:
    mf = state["matched_file"]
    print(f"\n⚙️ [VALIDATOR] Starting verification for {mf}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    print(f"   -> Executing get_file_report...")
    res_db = get_file_report.invoke({"file_name": state["matched_file"]})

    # --- NEW EXTRACTOR LOGIC ---
    # Extract the full Windows absolute path from the get_file_report result
    full_path = mf
    try:
        report_data = json.loads(res_db)
        if "file" in report_data:
            full_path = report_data["file"]
    except json.JSONDecodeError:
        pass
    # ---------------------------

    print(f"   -> Executing fetch_vue_block (script)...")
    res_code = fetch_vue_block.invoke({"file_path": full_path, "block": "script"})

    print(
        "⏳ [VALIDATOR] Tools finished. Asking LLM to verify data (This will take 10-20 seconds)..."
    )
    verify_prompt = (
        f"Analyze this DB report and Source Code.\n"
        f'Return ONLY JSON: {{"verified": bool, "false_positive": bool, "active_count": int, "fp_count": int, "evidence_lines": [int], "confidence": float}}\n\n'
        f"DB: {res_db}\nCode: {res_code}"
    )

    res = llm.invoke([HumanMessage(content=verify_prompt)])

    try:
        clean_json = re.sub(r"```json\s*|\s*```", "", res.content.strip())
        verification = json.loads(clean_json)
        state["verified"] = True
        state["tool_results"].append(
            f"VERIFICATION RESULT:\n{json.dumps(verification, indent=2)}"
        )
        print("✅ [VALIDATOR] LLM successfully output structured JSON.")
    except json.JSONDecodeError:
        state["verified"] = False
        print("⚠️ [VALIDATOR] LLM failed to output valid JSON.")

    state["tool_results"].extend([str(res_db), str(res_code)])
    return state


def synthesizer_node(state: GraphState) -> GraphState:
    print(
        "\n✍️ [SYNTHESIZER] Generating final English response (This will take 10-20 seconds)..."
    )
    results = state.get("tool_results", [])
    ctx = "\n\n---\n\n".join(results)

    clean_sys_msg = SystemMessage(
        content=(
            "You are the Code Audit Librarian. "
            "Your ONLY job is to synthesize the provided TOOL CONTEXT into a helpful, "
            "plain-English answer for the user. Do not try to call tools or ask the user "
            "to run tools. The data has already been fetched for you."
        )
    )

    prompt = (
        f"TOOL CONTEXT:\n{ctx}\n\n"
        f"USER QUERY: {state['user_query']}\n\n"
        f"Provide a clear, plain-English summary addressing the query using ONLY the context above."
    )

    res = llm.invoke([clean_sys_msg, HumanMessage(content=prompt)])
    state["final_answer"] = res.content
    print("✨ [SYNTHESIZER] Response generated!")
    print(f"{'=' * 50}\n")
    return state
