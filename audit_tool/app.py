import json
import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama

# Import ONLY what is globally available in prototype_agent
from prototype_agent import (
    execute_tool,
    extract_tool_call,
    looks_like_json,
    build_correction_message,
    clear_cache,
    SYSTEM_INSTRUCTIONS,
    _session_cache
)

# Initialize the LLM and System Message
llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0.0, num_ctx=8192)
system_msg = SystemMessage(content=SYSTEM_INSTRUCTIONS)

# Global conversation state for the Gradio session
conversation_turns = []

def chat_fn(message: str, history: list) -> str:
    global conversation_turns
    
    # --- BUG FIX: Sync backend memory with UI ---
    # If the Gradio history is empty (e.g., user clicked Clear or refreshed), wipe our memory!
    if len(history) == 0:
        print("\n[SYSTEM] UI chat cleared. Resetting backend memory.")
        conversation_turns.clear()
        
    print(f"\n{'='*50}")
    print(f"[USER ASKED]: {message}")
    
    conversation_turns.append(HumanMessage(content=message))
    
    # Trim to the last 12 items to protect the context window
    if len(conversation_turns) > 12:
        conversation_turns = conversation_turns[-12:]
        
    MAX_INNER_ITERATIONS = 6
    inner_iterations = 0
    
    trace_log = "<details><summary>🔍 <b>View Agent Trace</b></summary>\n\n"
    trace_entries = 0
    
    while inner_iterations < MAX_INNER_ITERATIONS:
        inner_iterations += 1
        
        try:
            full_history = [system_msg] + conversation_turns
            response = llm.invoke(full_history)
            ai_text = response.content.strip()
        except Exception as e:
            err_msg = f"[LLM Error] Ollama call failed: {e}"
            print(f"\n❌ {err_msg}")
            return err_msg

        # --- PATH A: Valid tool call ---
        tool_call = extract_tool_call(ai_text)
        if tool_call:
            t_name = tool_call.get("name")
            t_args = tool_call.get("arguments", {})
            
            cache_key = f"{t_name}:{t_args.get('file_path', '')}"
            if cache_key in _session_cache:
                msg = f"⚡ CACHE HIT: {t_name} | args: {t_args}"
                print(f"[AGENT TRACE] {msg}")
                trace_log += f"- {msg}\n"
            else:
                msg = f"🛠️ TOOL EXECUTED: {t_name} | args: {t_args}"
                print(f"[AGENT TRACE] {msg}")
                trace_log += f"- {msg}\n"
            
            trace_entries += 1
            conversation_turns.append(AIMessage(content=ai_text))
            
            try:
                tool_data = execute_tool(t_name, t_args)
            except Exception as e:
                tool_data = {"error": f"Tool execution failed: {e}"}
                print(f"[AGENT TRACE] ❌ ERROR: {e}")
                trace_log += f"- ❌ **ERROR**: {e}\n"
                
            observation = (
                f"TOOL RESULT for '{t_name}':\n"
                f"{json.dumps(tool_data, indent=2, default=str)}\n\n"
                f"Now answer the user's request ('{message}') using ONLY the data above.\n"
                "If they asked for specific lines or exact code, provide it exactly. "
                "Do NOT output JSON."
            )
            conversation_turns.append(HumanMessage(content=observation))
            print("[AGENT TRACE] Tool data fed back to model. Waiting for summary...")
            continue

        # --- PATH B: Hallucinated JSON answer ---
        if looks_like_json(ai_text):
            msg = "⚠️ HALLUCINATION DETECTED: Model output raw JSON instead of plain English. Forcing self-correction."
            print(f"[AGENT TRACE] {msg}")
            trace_log += f"- {msg}\n"
            trace_entries += 1
            
            conversation_turns.append(AIMessage(content=ai_text))
            conversation_turns.append(HumanMessage(content=build_correction_message(ai_text)))
            continue

        # --- PATH C: Clean natural-language answer ---
        print(f"[AGENT TRACE] Final Answer Generated:\n{ai_text}")
        print(f"{'='*50}\n")
        conversation_turns.append(AIMessage(content=ai_text))
        
        if trace_entries > 0:
            trace_log += "</details>\n\n---\n\n"
            return trace_log + ai_text
        else:
            return ai_text

    msg = "[Warning] Max iterations reached. Please rephrase your question."
    print(f"\n⚠️ {msg}")
    return msg


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