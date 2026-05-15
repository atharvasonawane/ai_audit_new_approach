import os
import networkx as nx
import logging

logger = logging.getLogger("graph_analyzer")

def find_entry_points(G: nx.DiGraph) -> list:
    """
    Entry points are the roots of the tree.
    Detection rules (first match wins):
    1. File is named App.vue, main.js, or main.ts
    2. File is inside a router/ or routes/ directory
    """
    entry_points = []
    for node in G.nodes:
        basename = os.path.basename(node)
        if basename in ('App.vue', 'main.js', 'main.ts'):
            entry_points.append(node)
        elif '/router/' in node or '/routes/' in node:
            entry_points.append(node)
            
    # Fallback if no specific roots are found: Use all nodes with 0 incoming edges
    if not entry_points:
        for node in G.nodes:
            if G.in_degree(node) == 0:
                entry_points.append(node)
                
    return entry_points

def compute_depths(G: nx.DiGraph, entry_points: list) -> dict:
    """
    Compute shortest path length from any entry point to each node.
    Returns -1 for unreachable nodes (orphans).
    """
    depths = {node: -1 for node in G.nodes}
    
    for ep in entry_points:
        if ep not in G.nodes:
            continue
        # Use single source shortest path to get lengths to all reachable nodes
        lengths = nx.single_source_shortest_path_length(G, ep)
        for node, length in lengths.items():
            if depths[node] == -1 or length < depths[node]:
                depths[node] = length
                
    return depths

def find_cycles(G: nx.DiGraph) -> list:
    """
    Detect circular dependencies with a length bound of 10 to prevent performance issues.
    """
    return list(nx.simple_cycles(G, length_bound=10))

def classify_node(node: str, in_degree: int, out_degree: int, depth: int, is_entry_point: bool) -> str:
    """
    Classify nodes strictly by priority:
    1. entry_point (in entry_points list)
    2. orphan (in_degree = 0, depth = -1, NOT entry_point)
    3. shared_utility (in_degree >= 5)
    4. hub (in_degree >= 3 and out_degree >= 3)
    5. leaf (out_degree = 0)
    6. standard (everything else)
    """
    if is_entry_point:
        return 'entry_point'
    elif in_degree == 0 and depth == -1:
        return 'orphan'
    elif in_degree >= 5:
        return 'shared_utility'
    elif in_degree >= 3 and out_degree >= 3:
        return 'hub'
    elif out_degree == 0:
        return 'leaf'
    else:
        return 'standard'

def analyze_graph(G: nx.DiGraph) -> dict:
    """
    Computes metrics for every node in the graph.
    Returns a dictionary mapping file path -> metrics dict.
    """
    logger.info("Starting graph analysis...")
    metrics = {}
    
    if G.number_of_nodes() == 0:
        logger.warning("Empty graph provided to analyzer.")
        return metrics
        
    entry_points = find_entry_points(G)
    depths = compute_depths(G, entry_points)
    cycles = find_cycles(G)
    
    # Pre-compute cycle membership for O(1) lookup
    nodes_in_cycles = set()
    for cycle in cycles:
        for node in cycle:
            nodes_in_cycles.add(node)
            
    for node in G.nodes:
        in_degree = G.in_degree(node)
        out_degree = G.out_degree(node)
        depth = depths[node]
        is_entry = node in entry_points
        
        # Impact Score: files with depth -1 (orphans) use depth=0 for this calculation
        calc_depth = max(depth, 0)
        impact_score = in_degree * (1 + calc_depth)
        
        node_category = classify_node(node, in_degree, out_degree, depth, is_entry)
        
        is_in_cycle = node in nodes_in_cycles
        my_cycles = [c for c in cycles if node in c]
        # Just grab the first cycle it belongs to for the cycle_members array as requested
        cycle_members = my_cycles[0] if my_cycles else []
        
        dependents = list(G.predecessors(node))
        dependencies = list(G.successors(node))
        transitive_dependents = list(nx.ancestors(G, node))
        
        metrics[node] = {
            "in_degree": in_degree,
            "out_degree": out_degree,
            "depth": depth,
            "impact_score": round(impact_score, 2),
            "node_category": node_category,
            "is_in_cycle": is_in_cycle,
            "cycle_members": cycle_members,
            "dependents": dependents,
            "dependencies": dependencies,
            "transitive_dependents": transitive_dependents
        }
        
    logger.info("Graph analysis complete.")
    return metrics
