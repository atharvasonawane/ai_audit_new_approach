import os
import json
import sqlite3
import logging
import networkx as nx

logger = logging.getLogger("graph_exporter")

def export_graph(G: nx.DiGraph, metrics: dict, project_name: str, db_path: str, frontend_public_dir: str):
    logger.info("Exporting dependency graph metrics to SQLite...")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # 1. Upsert into SQLite
        records = []
        for node, data in metrics.items():
            records.append((
                project_name,
                node,
                data["in_degree"],
                data["out_degree"],
                data["depth"],
                data["impact_score"],
                data["node_category"],
                1 if data["is_in_cycle"] else 0,
                json.dumps(data["cycle_members"]),
                json.dumps(data["dependents"]),
                json.dumps(data["dependencies"])
            ))
            
        conn.executemany("""
            INSERT INTO dependency_metrics (
                project_name, file_path, in_degree, out_degree, depth, impact_score, 
                node_category, is_in_cycle, cycle_members, dependents, dependencies
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_name, file_path) DO UPDATE SET
                in_degree=excluded.in_degree,
                out_degree=excluded.out_degree,
                depth=excluded.depth,
                impact_score=excluded.impact_score,
                node_category=excluded.node_category,
                is_in_cycle=excluded.is_in_cycle,
                cycle_members=excluded.cycle_members,
                dependents=excluded.dependents,
                dependencies=excluded.dependencies
        """, records)
        conn.commit()
        conn.close()
        logger.info(f"Successfully upserted {len(records)} node metrics into dependency_metrics table.")
    except Exception as e:
        logger.error(f"Failed to write to SQLite dependency_metrics: {e}")
        
    # 2. Export graph.json
    logger.info(f"Exporting graph.json to {frontend_public_dir}...")
    
    nodes = []
    edges = []
    
    for node, data in metrics.items():
        nodes.append({
            "id": node,
            "category": data["node_category"],
            "in_degree": data["in_degree"],
            "out_degree": data["out_degree"],
            "depth": data["depth"],
            "impact_score": data["impact_score"],
            "is_in_cycle": data["is_in_cycle"]
        })
        
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relationship_type": data.get("relationship_type", "utility")
        })
        
    orphans = [node for node, data in metrics.items() if data["node_category"] == "orphan"]
    
    cycles = []
    seen_cycles = set()
    for node, data in metrics.items():
        if data["is_in_cycle"] and data["cycle_members"]:
            c_tuple = tuple(sorted(data["cycle_members"]))
            if c_tuple not in seen_cycles:
                seen_cycles.add(c_tuple)
                cycles.append(data["cycle_members"])
                
    most_critical = None
    most_critical_in = 0
    if metrics:
        most_critical_node = max(metrics.items(), key=lambda x: x[1]["impact_score"])
        most_critical = most_critical_node[0]
        most_critical_in = most_critical_node[1]["in_degree"]
        
    max_depth = max([data["depth"] for data in metrics.values()] + [0])
    
    summary = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "orphan_count": len(orphans),
        "cycle_count": len(cycles),
        "max_depth": max_depth,
        "most_critical_file": most_critical,
        "most_critical_file_in_degree": most_critical_in
    }
    
    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "cycles": cycles,
        "orphans": orphans
    }
    
    try:
        os.makedirs(frontend_public_dir, exist_ok=True)
        out_file = os.path.join(frontend_public_dir, "graph.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2)
            
        logger.info(f"Graph export complete. JSON saved to {out_file}")
    except Exception as e:
        logger.error(f"Failed to write graph.json: {e}")
