import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama

import gradio as gr
from agent.graph import agent as librarian_agent
from agent.state import GraphState
# Import ONLY what is globally available in prototype_agent
from prototype_agent import (
    execute_tool,
    extract_tool_call,
    looks_like_json,
    build_correction_message,
    clear_cache,
    SYSTEM_INSTRUCTIONS,
)

# Initialize the LLM and System Message
llm = ChatOllama(model="qwen2.5-coder:3b", temperature=0.0, num_ctx=8192)
system_msg = SystemMessage(content=SYSTEM_INSTRUCTIONS)

# Global conversation state for the Gradio session
conversation_turns = []

def chat_fn(message: str, history: list) -> str:
    # Initialize the strict state dictionary
    initial_state = GraphState(
        user_query=message, 
        query_type="", 
        matched_file="",
        tool_results=[], 
        final_answer="", 
        verified=False, 
        error=""
    )
    
    # Execute the LangGraph State Machine
    result = librarian_agent.invoke(initial_state)
    answer = result.get("final_answer", "No answer generated.")
    
    # Route trace appended under answer
    route     = result.get("query_type", "unknown")
    file_hit  = result.get("matched_file", "")
    tools_n   = len(result.get("tool_results", []))
    verified  = "✓ verified" if result.get("verified") else ""
    
    trace = f"\n\n---\n*Route: `{route}`"
    if file_hit: 
        trace += f" · File: `{file_hit}`"
    trace += f" · Tools called: {tools_n}"
    if verified: 
        trace += f" · {verified}"
    trace += "*"
    
    return answer + trace


# Build the Gradio UI
with gr.Blocks(title="Code Audit Librarian") as demo:
    gr.Markdown("# Code Audit Librarian")
    gr.Markdown("Ask anything about the Vue.js codebase. All answers are sourced from static analysis data.")
    
    gr.ChatInterface(
        fn=chat_fn,
        examples=[
            "Which files are most dangerous to refactor?",
            "How risky is RoleMgt.vue?",
            "Can you show me the script block for RoleMgt.vue?",
            "Which components have accessibility violations?"
        ]
    )
    
    gr.Markdown("*Powered by qwen2.5-coder via Ollama*")

if __name__ == "__main__":
    demo.launch()