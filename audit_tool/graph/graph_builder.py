import sqlite3
import networkx as nx
import logging

logger = logging.getLogger("graph_builder")

def build_graph(project_name: str, db_path: str) -> nx.DiGraph:
    """
    Reads component_relationships from SQLite and builds a networkx.DiGraph.
    Every node is a file path string.
    Every edge is a directed import relationship with a relationship_type.
    """
    logger.info(f"Building dependency graph for project: {project_name}")
    G = nx.DiGraph()
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT parent_file, child_file, relationship_type FROM component_relationships WHERE project_name = ?",
            (project_name,)
        ).fetchall()
        
        for row in rows:
            parent = row["parent_file"]
            child = row["child_file"]
            rel_type = row["relationship_type"]
            
            # The directed edge points from parent (the importer) to child (the imported file)
            # This represents the "depends on" relationship. 
            # Alternatively, it could represent "data flow". We use parent -> child as specified.
            G.add_edge(parent, child, relationship_type=rel_type)
            
        conn.close()
        logger.info(f"Graph built successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        
    return G
