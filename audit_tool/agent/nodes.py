import re
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from agent.state import GraphState

# Added imports for Phase 2:
from tools.db_tools import get_high_risk_files, get_file_report, get_summary_stats, get_critical_files, get_files_by_module, get_flag_summary
from tools.code_tools import fetch_vue_block

# Initialize the LLM and System Message locally
llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=8192)


def router_node(state: GraphState) -> GraphState:
    query = state["user_query"].lower()
    print(f"\n{'=' * 50}")
    print(f"🕵️ [ROUTER] Analyzing user query: '{query}'")

    # 1. VERIFY CHECK (Highest Priority)
    verify_patterns = ["false positive", "verify", "confirm", "are these real", "check if"]
    if any(p in query for p in verify_patterns):
        state["query_type"] = "verify"
        match = re.search(r'[\w/\\]+\.vue', state["user_query"], re.IGNORECASE)
        state["matched_file"] = match.group(0) if match else ""
        return state

    # 2. FILE CHECK (.vue regex) - MOVED BEFORE SUMMARY
    match = re.search(r'[\w/\\]+\.vue', state["user_query"], re.IGNORECASE)
    if match:
        state["query_type"] = "file"
        state["matched_file"] = match.group(0)
        return state

    # 3. SUMMARY KEYWORDS (Includes new keywords for statistics)
    summary_keywords = [
        "list", "all files", "overview", "codebase", "dangerous", 
        "critical", "high risk", "worst", "most issues", "which files", 
        "most dangerous", "statistics", "static analysis"
    ]
    if any(k in query for k in summary_keywords):
        state["query_type"] = "summary"
        return state

    # 4. FILE PHRASE PATTERNS (Secondary safety net for files)
    file_phrases = [
        "tell me about", "what about", "show me", "explain", 
        "describe", "how is", "how risky is", 
        "looking at", "full report for", "report for"
    ]
    if any(p in query for p in file_phrases):
        state["query_type"] = "file"
        return state

    # 5. LLM FALLBACK 
    state["matched_file"] = ""
    print("⏳ [ROUTER] No regex match. Asking LLM to classify...")
    prompt = f"Classify this query into one exact word: 'summary', 'file', 'verify', or 'unknown'. Query: {state['user_query']}"
    res = llm.invoke([HumanMessage(content=prompt)])
    clean_res = res.content.strip().lower()
    
    matched_type = clean_res if clean_res in ["summary", "file", "verify"] else "unknown"
    state["query_type"] = matched_type
    
    print(f"🎯 [ROUTER] Decided Route: {matched_type.upper()}")
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
    print(f"\n⚙️ [DEEP DIVE] Fetching DB report for {state.get('matched_file', '')}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    matched_file = state.get("matched_file", "")
    query = state.get("user_query", "").lower()
    
    stopwords = [
        "tell", "me", "about", "what", "show", "give", "details", "on", 
        "explain", "describe", "file", "the", "a", "an", "is", "how", 
        "risky", "for", "of", "please", "can", "you"
    ]
    generic_words = {"login", "stuff", "page", "component", "file"}
    
    search_term = matched_file
    
    if not search_term:
        clean_query = query.replace("?", "").replace(".", "").replace(",", "")
        words = clean_query.split()
        remaining_words = [w for w in words if w not in stopwords]
        search_term = " ".join(remaining_words).strip()
        print(f"📄 [DEEP DIVE] Extracted search term: '{search_term}'")
        
    has_vue = ".vue" in search_term.lower()
    is_long_enough = len(search_term) > 4
    is_not_generic = search_term not in generic_words
    
    if has_vue or (is_long_enough and is_not_generic):
        state["matched_file"] = search_term
        res_db = get_file_report.invoke({"file_name": search_term})
        state["tool_results"].append(str(res_db))
    else:
        state["tool_results"].append('{"error": "Ambiguous file query"}')
        state["final_answer"] = "Please specify the exact .vue filename you are asking about."
        
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
