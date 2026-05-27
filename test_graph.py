import os
import yaml
import sys
from pathlib import Path

# Ensure paths are set up correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(1, os.path.join(os.path.abspath(os.path.dirname(__file__)), "audit_tool"))

from audit_tool.graph.graph_builder import build_graph
from audit_tool.graph.graph_analyzer import analyze_graph
from audit_tool.graph.graph_exporter import export_graph

def main():
    config_path = "audit_tool/config/project_config.yaml"
    if not os.path.exists(config_path):
        print(f"Config not found at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    project_name = config.get("project_name")
    
    # In run_audit.py, db_path is usually audit_history.db in the root
    db_path = str(Path("audit_history.db").absolute())

    print("=" * 60)
    print(f"TESTING GRAPH BUILDER & ANALYZER")
    print(f"Project Name: {project_name}")
    print(f"Database: {db_path}")
    print("=" * 60)

    # 1. Build the graph
    print("\n[1] Building Graph...")
    G = build_graph(project_name, db_path)
    
    # 2. Analyze the graph
    print("\n[2] Analyzing Graph...")
    metrics = analyze_graph(G)

    # 3. Export the graph
    print("\n[3] Exporting Graph (SQLite + JSON)...")
    frontend_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "report", "frontend", "public")
    export_graph(G, metrics, project_name, db_path, frontend_dir)
    print(f"Export finished. Check {frontend_dir}/graph.json")

if __name__ == "__main__":
    main()
