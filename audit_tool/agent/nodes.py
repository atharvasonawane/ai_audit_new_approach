import re
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from prototype_agent import execute_tool, extract_tool_call, SYSTEM_INSTRUCTIONS
from agent.state import GraphState

# Initialize the LLM and System Message locally
llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=8192)

def router_node(state: GraphState) -> GraphState:
    query = state["user_query"].lower()
    print(f"\n{'='*50}")
    print(f"🕵️ [ROUTER] Analyzing user query: '{query}'")
    
    patterns = {
        "verify":  [r"false positive", r"verify", r"actually (have|contain)", r"double.?check", r"confirm"],
        "summary": [r"most (dangerous|risky|critical)", r"which files", r"overall.*(health|status)", r"top \d+", r"highest risk"],
        "file":    [r"\.vue\b", r"how risky is", r"tell me about", r"what flags", r"deep.?dive"]
    }
    
    matched_type = "unknown"
    for q_type, pats in patterns.items():
        if any(re.search(p, query) for p in pats):
            matched_type = q_type
            break
            
    file_match = re.search(r'[\w/\\]+\.vue', state["user_query"], re.IGNORECASE)
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
    
    res = execute_tool("get_high_risk_files", {})
    labeled_result = f"DATABASE REPORT - THE FOLLOWING FILES ARE FLAGGED AS HIGH RISK/DANGEROUS:\n{res}"
    state["tool_results"].append(labeled_result)
    return state

def deep_dive_node(state: GraphState) -> GraphState:
    print(f"\n⚙️ [DEEP DIVE] Fetching DB report for {state['matched_file']}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []
        
    mf = state["matched_file"]
    if not mf:
        print("⏳ [DEEP DIVE] File name missing. Asking LLM to extract...")
        prompt = f"Extract the .vue filename from this query. Output ONLY the filename. Query: {state['user_query']}"
        res = llm.invoke([HumanMessage(content=prompt)])
        mf = res.content.strip()
        print(f"📄 [DEEP DIVE] LLM extracted: {mf}")
        
    res_db = execute_tool("get_file_database_report", {"file_path": mf})
    state["matched_file"] = mf
    state["tool_results"].append(str(res_db))
    return state

def validator_node(state: GraphState) -> GraphState:
    mf = state["matched_file"]
    print(f"\n⚙️ [VALIDATOR] Starting verification for {mf}...")
    if "tool_results" not in state or state["tool_results"] is None:
        state["tool_results"] = []
        
    print(f"   -> Executing get_file_database_report...")
    res_db = execute_tool("get_file_database_report", {"file_path": mf})
    
    print(f"   -> Executing fetch_vue_block (script)...")
    res_code = execute_tool("fetch_vue_block", {"file_path": mf, "block_type": "script"})
    
    print("⏳ [VALIDATOR] Tools finished. Asking LLM to verify data (This will take 10-20 seconds)...")
    verify_prompt = (
        f"Analyze this DB report and Source Code.\n"
        f"Return ONLY JSON: {{\"verified\": bool, \"false_positive\": bool, \"active_count\": int, \"fp_count\": int, \"evidence_lines\": [int], \"confidence\": float}}\n\n"
        f"DB: {res_db}\nCode: {res_code}"
    )
    
    res = llm.invoke([HumanMessage(content=verify_prompt)])
    
    try:
        clean_json = re.sub(r"```json\s*|\s*```", "", res.content.strip())
        json.loads(clean_json)
        state["verified"] = True
        print("✅ [VALIDATOR] LLM successfully output structured JSON.")
    except json.JSONDecodeError:
        state["verified"] = False
        print("⚠️ [VALIDATOR] LLM failed to output valid JSON.")
        
    state["tool_results"].extend([str(res_db), str(res_code)])
    return state

def synthesizer_node(state: GraphState) -> GraphState:
    print("\n✍️ [SYNTHESIZER] Generating final English response (This will take 10-20 seconds)...")
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
    print(f"{'='*50}\n")
    return state