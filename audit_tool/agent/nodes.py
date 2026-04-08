import re
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from agent.state import GraphState

# Added imports for Phase 2:
from tools.db_tools import get_high_risk_files, get_file_report, get_summary_stats, get_critical_files, get_files_by_module, get_flag_summary
from tools.code_tools import fetch_vue_block

# Initialize the LLM and System Message locally
llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=1024)


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

    # 2. CODE VIEW CHECK (Must run before general file check)
    code_view_patterns = [
        r"show me.*(script|template|style)",
        r"(script|template|style) block",
        r"source code",
        r"read.*\.vue"
    ]
    if any(re.search(p, query) for p in code_view_patterns):
        state["query_type"] = "code_view"
        match = re.search(r'[\w/\\]+\.vue', state["user_query"], re.IGNORECASE)
        state["matched_file"] = match.group(0) if match else ""
        return state

    # 3. FILE CHECK (.vue regex)
    match = re.search(r'[\w/\\]+\.vue', state["user_query"], re.IGNORECASE)
    if match:
        state["query_type"] = "file"
        state["matched_file"] = match.group(0)
        return state

    # 4. SUMMARY KEYWORDS
    summary_keywords = [
        "list", "all files", "overview", "codebase", "dangerous", 
        "critical", "high risk", "worst", "most issues", "which files", 
        "most dangerous", "statistics", "static analysis"
    ]
    if any(k in query for k in summary_keywords):
        state["query_type"] = "summary"
        return state

    # 5. FILE PHRASE PATTERNS
    file_phrases = [
        "tell me about", "what about", "show me", "explain", 
        "describe", "how is", "how risky is", 
        "looking at", "full report for", "report for"
    ]
    if any(p in query for p in file_phrases):
        state["query_type"] = "file"
        return state

    # 6. LLM FALLBACK 
    state["matched_file"] = ""
    print("⏳ [ROUTER] No regex match. Asking LLM to classify...")
    prompt = f"Classify this query into one exact word: 'summary', 'file', 'verify', or 'unknown'. Query: {state['user_query']}"
    res = llm.invoke([HumanMessage(content=prompt)])
    clean_res = res.content.strip().lower()
    
    matched_type = clean_res if clean_res in ["summary", "file", "verify", "code_view"] else "unknown"
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


def code_view_node(state: GraphState) -> GraphState:
    mf = state.get("matched_file", "")
    print(f"\n⚙️ [CODE VIEW] Preparing source extraction for {mf}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    # Step 1: Get the absolute path from the DB report
    # This is critical because fetch_vue_block needs the real disk location [cite: 140, 159]
    res_db = get_file_report.invoke({"file_name": mf})
    full_path = mf
    try:
        report_data = json.loads(res_db)
        full_path = report_data.get("file", mf)
    except:
        pass

    # Step 2: Determine which block the user wants
    query = state.get("user_query", "").lower()
    block_type = "script" # Default
    if "template" in query:
        block_type = "template"
    elif "style" in query:
        block_type = "style"

    # Step 3: Fetch the raw code
    print(f"   -> Executing fetch_vue_block for {block_type}...")
    res_code = fetch_vue_block.invoke({"file_path": full_path, "block": block_type})
    
    # Store the result for the synthesizer [cite: 180, 243]
    state["tool_results"].append(f"SOURCE CODE ({block_type.upper()} BLOCK):\n{res_code}")
    return state


def validator_node(state: GraphState) -> GraphState:
    mf = state["matched_file"]
    print(f"\n⚙️ [VALIDATOR] Starting verification for {mf}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []

    print(f"   -> Executing get_file_report...")
    res_db = get_file_report.invoke({"file_name": state["matched_file"]})

    # --- NEW EXTRACTOR LOGIC ---
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
        f'Return ONLY JSON: {{"verified": bool, "false_positive": bool, "active_count": int, "fp_count": int, "evidence_lines": [int], "confidence": float}}\n\n'
        f"DB: {res_db}\nCode: {res_code}"
    )

    messages = [HumanMessage(content=verify_prompt)]
    res = llm.invoke(messages)

    def extract_json(content: str):
        clean_json = re.sub(r"```json\s*|\s*```", "", content.strip())
        return json.loads(clean_json)

    try:
        verification = extract_json(res.content)
        state["verified"] = True
        state["tool_results"].append(
            f"VERIFICATION RESULT:\n{json.dumps(verification, indent=2)}"
        )
        print("✅ [VALIDATOR] LLM successfully output structured JSON.")
        
    except json.JSONDecodeError:
        print("⚠️ [VALIDATOR] LLM output prose instead of JSON. Sending correction message...")
        messages.append(res)
        messages.append(HumanMessage(content=(
            "You failed to return valid JSON. You MUST return strictly a JSON object "
            "matching the requested schema. Do not include prose, explanations, or markdown formatting."
        )))
        
        res_retry = llm.invoke(messages)
        try:
            verification = extract_json(res_retry.content)
            state["verified"] = True
            state["tool_results"].append(
                f"VERIFICATION RESULT:\n{json.dumps(verification, indent=2)}"
            )
            print("✅ [VALIDATOR] LLM successfully output structured JSON on retry.")
        except json.JSONDecodeError:
            state["verified"] = False
            state["tool_results"].append(
                "VERIFICATION FAILED: Validator returned prose instead of strict JSON. Could not verify false positives."
            )
            print("❌ [VALIDATOR] LLM failed to output valid JSON after retry. Verification skipped.")

    state["tool_results"].extend([str(res_db), str(res_code)])
    return state


def synthesizer_node(state: GraphState) -> GraphState:
    print("\n✍️ [SYNTHESIZER] Analyzing context and generating response...")
    results = state.get("tool_results", [])
    ctx = "\n\n---\n\n".join(results)

    # This prompt is designed to work with 3B (short extractions) 
    # and 27B (full file analysis) [cite: 308, 333]
    clean_sys_msg = SystemMessage(
        content=(
            "You are the Code Audit Librarian. Your job is to answer the user's "
            "question using ONLY the provided TOOL CONTEXT. [cite: 181, 290]"
            "\n- If the user asks for code, provide the relevant snippets in markdown blocks."
            "\n- If the requested code is very long, focus on the most important logic."
            "\n- Do not use outside knowledge or hallucinate code. [cite: 186, 290]"
        )
    )

    prompt = (
        f"TOOL CONTEXT:\n{ctx}\n\n"
        f"USER QUERY: {state['user_query']}\n\n"
        "Please provide the specific information requested."
    )

    res = llm.invoke([clean_sys_msg, HumanMessage(content=prompt)])
    state["final_answer"] = res.content
    print("✨ [SYNTHESIZER] Answer ready.")
    return state