# test_phase3.py

import time
import json
import os
from benchmark_queries import BENCHMARK_QUERIES

# Change 'app' to whatever your compiled graph is actually named in agent/graph.py
from agent.graph import agent as librarian_agent 
from agent.state import GraphState

OUTPUT_FILE = "benchmark_raw_results.json"

def run_benchmarks():
    results = []
    passed_count = 0

    for item in BENCHMARK_QUERIES:
        q_id = item["id"]
        query_text = item["query"]
        expected_route = item["expected_route"]
        notes = item["notes"]

        print(f"Running [{q_id}/20] {query_text}")

        initial_state: GraphState = {
            "user_query": query_text,
            "query_type": "",
            "matched_file": "",
            "tool_results": [],
            "final_answer": "",
            "verified": False,
            "error": ""
        }

        start_time = time.time()
        actual_route = ""
        final_answer = ""
        error_str = ""

        try:
            result = librarian_agent.invoke(initial_state)
            actual_route = result.get("query_type", "")
            final_answer = result.get("final_answer", "")
            error_str = result.get("error", "")
        except Exception as e:
            error_str = str(e)
            actual_route = "error"
            final_answer = ""

        elapsed = round(time.time() - start_time, 2)

        is_pass = (actual_route == expected_route)
        pass_fail_str = "PASS" if is_pass else "FAIL"
        
        if is_pass:
            passed_count += 1

        answer_snippet = final_answer[:200]

        result_dict = {
            "id": q_id,
            "query": query_text,
            "expected_route": expected_route,
            "actual_route": actual_route,
            "pass_fail": pass_fail_str,
            "answer_snippet": answer_snippet,
            "error": error_str,
            "elapsed_seconds": elapsed,
            "notes": notes
        }
        
        results.append(result_dict)

        print(f"[{pass_fail_str}] — expected: {expected_route} | got: {actual_route} | {elapsed}s\n")

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print final summary table
    print("-" * 85)
    print("PHASE 3 BENCHMARK RESULTS")
    print(f"{'ID':<3} | {'Query (first 40 chars)':<40} | {'Expected':<10} | {'Actual':<10} | {'Pass/Fail':<9} | {'Time'}")
    print("-" * 85)

    for r in results:
        q_trunc = r["query"][:37] + "..." if len(r["query"]) > 40 else r["query"]
        print(f"{r['id']:<3} | {q_trunc:<40} | {r['expected_route']:<10} | {r['actual_route']:<10} | {r['pass_fail']:<9} | {r['elapsed_seconds']:<6}")

    print("-" * 85)
    print(f"Total: {passed_count}/20 PASSED")
    print(f"Raw results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_benchmarks()