import sys
from langchain_ollama import ChatOllama

# Project imports
from prototype_agent import DB_CFG, db_report_loader, execute_tool
from agent.graph import agent as librarian_agent
from agent.state import GraphState
from agent.nodes import router_node


def run_tests():
    print("Starting Phase 1 Tests...\n")
    results = {
        "CHECK 1": "FAIL",
        "CHECK 2": "FAIL",
        "CHECK 3": "FAIL",
        "CHECK 4": "FAIL",
        "CHECK 5": "FAIL",
    }

    # ==========================================
    # CHECK 1 — Database connection
    # ==========================================
    print("Running CHECK 1: Database connection...")
    try:
        db_report_loader.get_db_connection(DB_CFG).close()
        results["CHECK 1"] = "PASS"
        print("  -> Success")
    except Exception as e:
        print(f"  -> Exception: {e}")

    # ==========================================
    # CHECK 2 — Ollama is running
    # ==========================================
    print("\nRunning CHECK 2: Ollama is running...")
    try:
        llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=512)
        res = llm.invoke("say hello")
        if res.content and res.content.strip():
            results["CHECK 2"] = "PASS"
            print("  -> Success")
        else:
            print("  -> Failure: Empty response received.")
    except Exception as e:
        print("  -> Is Ollama running? Try: ollama serve")
        print(f"  -> Original Exception: {e}")

    # ==========================================
    # CHECK 3 — get_high_risk_files tool returns data
    # ==========================================
    print("\nRunning CHECK 3: get_high_risk_files tool...")
    try:
        res = execute_tool("get_high_risk_files", {})
        if isinstance(res, dict) and "error" in res:
            print(f"  -> Failure: Tool returned error: {res['error']}")
        elif isinstance(res, list) and len(res) > 0:
            results["CHECK 3"] = "PASS"
            print("  -> Success")
        else:
            print(f"  -> Failure: Result is empty or unexpected type: {res}")
    except Exception as e:
        print(f"  -> Exception: {e}")

    # ==========================================
    # CHECK 4 — LangGraph graph compiles and runs one query
    # ==========================================
    print("\nRunning CHECK 4: LangGraph execution...")
    try:
        state = GraphState(
            user_query="which files are most dangerous?",
            query_type="",
            matched_file="",
            tool_results=[],
            final_answer="",
            verified=False,
            error="",
        )
        res = librarian_agent.invoke(state)
        if res.get("final_answer") and str(res["final_answer"]).strip():
            results["CHECK 4"] = "PASS"
            print("  -> Success")
        else:
            print("  -> Failure: Empty final_answer in state.")
    except Exception as e:
        print(f"  -> Exception: {e}")

    # ==========================================
    # CHECK 5 — Router routes correctly
    # ==========================================
    print("\nRunning CHECK 5: Router logic...")
    try:
        test_cases = [
            ("which files are most dangerous?", "summary"),
            ("how risky is UserProfile.vue?", "file"),
            ("are these flags false positives?", "verify"),
        ]

        all_passed = True
        for query, expected_route in test_cases:
            state = GraphState(
                user_query=query,
                query_type="",
                matched_file="",
                tool_results=[],
                final_answer="",
                verified=False,
                error="",
            )
            res = router_node(state)
            actual_route = res.get("query_type")

            if actual_route != expected_route:
                all_passed = False
                print(
                    f"  -> Failure: Query '{query}' returned '{actual_route}' (Expected: '{expected_route}')"
                )

        if all_passed:
            results["CHECK 5"] = "PASS"
            print("  -> Success")
    except Exception as e:
        print(f"  -> Exception: {e}")

    # ==========================================
    # FINAL RESULTS
    # ==========================================
    passed_count = list(results.values()).count("PASS")

    print("\n==================")
    print("PHASE 1 RESULTS")
    print("==================")
    print(f"CHECK 1 - DB Connection:     {results['CHECK 1']}")
    print(f"CHECK 2 - Ollama Running:    {results['CHECK 2']}")
    print(f"CHECK 3 - Tools Return Data: {results['CHECK 3']}")
    print(f"CHECK 4 - LangGraph Runs:    {results['CHECK 4']}")
    print(f"CHECK 5 - Router Correct:    {results['CHECK 5']}")
    print("==================")
    print(f"{passed_count}/5 checks passed\n")

    if passed_count == 5:
        print("✅ PHASE 1 COMPLETE")
    else:
        print("❌ PHASE 1 INCOMPLETE — fix failures before Phase 2")


if __name__ == "__main__":
    run_tests()
