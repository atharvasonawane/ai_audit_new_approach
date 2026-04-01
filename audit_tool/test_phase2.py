import json
from tools.data_loader import get_report, get_files
from tools.db_tools import get_high_risk_files, get_summary_stats, get_file_report
from agent.state import GraphState

passes = 0

# CHECK 1: data_loader loads correctly
try:
    report = get_report()
    assert isinstance(report, dict), "Result is not a dict"
    assert "summary" in report, "Missing 'summary' key"
    assert "files" in report, "Missing 'files' key"
    print("CHECK 1: data_loader — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 1: data_loader — FAIL: {e}")

# CHECK 2: get_files returns data
try:
    files = get_files()
    assert isinstance(files, list), "Result is not a list"
    assert len(files) > 0, "List is empty"
    print("CHECK 2: get_files — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 2: get_files — FAIL: {e}")

# CHECK 3: get_high_risk_files tool works
try:
    res_str = get_high_risk_files.invoke({})
    res_json = json.loads(res_str)
    assert isinstance(res_json, list), "Parsed JSON is not a list"
    assert len(res_json) > 0, "List is empty"
    print("CHECK 3: get_high_risk_files — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 3: get_high_risk_files — FAIL: {e}")

# CHECK 4: get_summary_stats tool works
try:
    res_str = get_summary_stats.invoke({})
    res_json = json.loads(res_str)
    assert "total_files_scanned" in res_json, "Missing 'total_files_scanned' key"
    print("CHECK 4: get_summary_stats — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 4: get_summary_stats — FAIL: {e}")

# CHECK 5: get_file_report tool works
try:
    res_str = get_file_report.invoke({"file_name": "RoleMgt"})
    res_json = json.loads(res_str)
    assert "error" not in res_json, "Result contains 'error' key"
    assert "risk_level" in res_json, "Missing 'risk_level' key"
    print("CHECK 5: get_file_report — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 5: get_file_report — FAIL: {e}")

# CHECK 6: End-to-end LangGraph agent works
try:
    import agent.graph
    from agent.state import GraphState
    
    # Dynamically find the compiled LangGraph object (ignoring the exact variable name)
    librarian_agent = None
    for name in dir(agent.graph):
        obj = getattr(agent.graph, name)
        # A compiled LangGraph object has both 'invoke' and 'get_graph' methods
        if hasattr(obj, "invoke") and hasattr(obj, "get_graph") and not isinstance(obj, type):
            librarian_agent = obj
            break
            
    if librarian_agent is None:
        raise ImportError(f"Could not find compiled graph in agent.graph. Found attributes: {[n for n in dir(agent.graph) if not n.startswith('__')]}")

    initial_state = GraphState(
        user_query="Which files are most dangerous?",
        query_type="",
        matched_file="",
        tool_results=[],
        final_answer="",
        verified=False,
        error=""
    )
    result = librarian_agent.invoke(initial_state)
    assert "final_answer" in result, "Result missing 'final_answer' key"
    assert isinstance(result["final_answer"], str), "final_answer is not a string"
    assert len(result["final_answer"].strip()) > 0, "final_answer is an empty string"
    print("CHECK 6: LangGraph end-to-end — PASS")
    passes += 1
except Exception as e:
    print(f"CHECK 6: LangGraph end-to-end — FAIL: {e}")

# Final completion check
if passes == 6:
    print(f"{passes}/6 PASS — PHASE 2 COMPLETE")
else:
    print(f"{passes}/6 PASS — PHASE 2 INCOMPLETE")