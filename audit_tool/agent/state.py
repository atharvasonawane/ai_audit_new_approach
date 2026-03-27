from typing import TypedDict, List

class GraphState(TypedDict):
    user_query: str
    query_type: str      # "summary" | "file" | "verify" | "unknown"
    matched_file: str
    tool_results: List[str]
    final_answer: str
    verified: bool
    error: str