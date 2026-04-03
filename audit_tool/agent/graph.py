from langgraph.graph import StateGraph, END
from agent.state import GraphState
from agent.nodes import router_node, aggregator_node, deep_dive_node, validator_node, synthesizer_node, code_view_node

def build_graph():
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("aggregator", aggregator_node)
    workflow.add_node("deep_dive", deep_dive_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("code_view", code_view_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Routing logic
    def route_edge(state: GraphState):
        return state["query_type"]
        
    workflow.add_conditional_edges("router", route_edge, {
        "summary": "aggregator",
        "file": "deep_dive",
        "verify": "validator",
        "code_view": "code_view",
        "unknown": "aggregator"  # Fallback
    })
    
    # All branches flow to synthesizer
    workflow.add_edge("aggregator", "synthesizer")
    workflow.add_edge("deep_dive", "synthesizer")
    workflow.add_edge("validator", "synthesizer")
    workflow.add_edge("code_view", "synthesizer")
    
    # End
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()
    
agent = build_graph()