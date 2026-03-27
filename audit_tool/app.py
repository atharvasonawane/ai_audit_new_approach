import threading
import gradio as gr
from agent.graph import agent as librarian_agent
from agent.state import GraphState

# --- NEW IMPORTS ---
from prototype_agent import DB_CFG
from feedback.feedback_logger import create_feedback_table, log_feedback

# --- NEW SETUP ---
# Initialize the database table once at startup
create_feedback_table(DB_CFG)

# Use threading.local() so each Gradio worker thread has its own isolated state.
# Prevents one user's button click from logging another user's answer.
_local = threading.local()

def _get_last() -> dict:
    """Return this thread's last_result, initialising it if needed."""
    if not hasattr(_local, "last_result"):
        _local.last_result = {"query": "", "answer": "", "file_path": "", "tool_used": ""}
    return _local.last_result

def chat_fn(message: str, history: list) -> str:
    last_result = _get_last()
    
    initial_state = GraphState(
        user_query=message, 
        query_type="", 
        matched_file="",
        tool_results=[], 
        final_answer="", 
        verified=False, 
        error=""
    )
    
    result = librarian_agent.invoke(initial_state)
    answer = result.get("final_answer", "No answer generated.")
    
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
    
    # --- NEW: Update module-level tracking ---
    last_result["query"] = message
    last_result["answer"] = answer
    last_result["file_path"] = file_hit
    last_result["tool_used"] = route
    
    return answer + trace


with gr.Blocks(title="Code Audit Librarian") as demo:
    gr.Markdown("# Code Audit Librarian")
    gr.Markdown("Ask anything about the Vue.js codebase. All answers are sourced from static analysis data.")
    
    # Assign the ChatInterface to a variable so we can attach events to it
    chat_ui = gr.ChatInterface(
        fn=chat_fn,
        examples=[
            "Which files are most dangerous to refactor?",
            "How risky is RoleMgt.vue?",
            "Can you show me the script block for RoleMgt.vue?",
            "Which components have accessibility violations?"
        ]
    )
    
    wrong_btn = gr.Button("👎 Wrong answer")
    
    def flag_wrong():
        last_result = _get_last()
        log_feedback(
            DB_CFG, 
            last_result["query"], 
            last_result["file_path"],
            last_result["tool_used"], 
            last_result["answer"], 
            {}, 
            False
        )
        # Update text AND disable the button to prevent spam
        return gr.update(value="✓ Logged — thank you", interactive=False)
        
    wrong_btn.click(fn=flag_wrong, inputs=[], outputs=[wrong_btn])
    
    # --- NEW: Reset the button when the chat updates ---
    def reset_btn():
        return gr.update(value="👎 Wrong answer", interactive=True)
        
    chat_ui.chatbot.change(fn=reset_btn, inputs=[], outputs=[wrong_btn])
    
    gr.Markdown("*Powered by qwen2.5-coder via Ollama*")

if __name__ == "__main__":
    demo.launch()