import os
import sqlite3
import yaml
import sys
from pathlib import Path

# Ensure paths are set up correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(1, os.path.join(os.path.abspath(os.path.dirname(__file__)), "audit_tool"))

from db.db_init import init_db
from audit_tool.graph.import_extractor import run_import_extraction

def main():
    config_path = "audit_tool/config/project_config.yaml"
    if not os.path.exists(config_path):
        print(f"Config not found at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    base_path = config.get("base_path")
    project_name = config.get("project_name")
    
    # In run_audit.py, db_path is usually audit_history.db in the root
    db_path = str(Path("audit_history.db").absolute())

    print("=" * 60)
    print(f"TESTING IMPORT EXTRACTOR")
    print(f"Project Name: {project_name}")
    print(f"Target Path: {base_path}")
    print(f"Database: {db_path}")
    print("=" * 60)

    # 1. Initialize DB to create new tables
    print("\n[1] Initializing DB schema...")
    init_db(db_path)
    
    # 2. Run the Extractor
    print("\n[2] Running Import Extraction (this will parse all files)...")
    run_import_extraction(base_path, project_name, db_path)
    
    # 3. Verification Queries
    print("\n[3] Verification Queries")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query relationships count
    cursor.execute("SELECT COUNT(*) as count FROM component_relationships WHERE project_name=?", (project_name,))
    rel_count = cursor.fetchone()["count"]
    print(f"  -> Total component relationships extracted: {rel_count}")

    if rel_count > 0:
        print("\n  -> Sample 3 relationships:")
        cursor.execute("SELECT parent_file, child_file, relationship_type FROM component_relationships WHERE project_name=? LIMIT 3", (project_name,))
        for row in cursor.fetchall():
            print(f"       {row['parent_file']} ---> {row['child_file']} [{row['relationship_type']}]")

    # Query unresolved imports count
    cursor.execute("SELECT COUNT(*) as count FROM unresolved_imports WHERE project_name=?", (project_name,))
    unresolved_count = cursor.fetchone()["count"]
    print(f"\n  -> Total unresolved imports: {unresolved_count}")

    if unresolved_count > 0:
        print("\n  -> Sample 3 unresolved imports:")
        cursor.execute("SELECT parent_file, raw_import, reason FROM unresolved_imports WHERE project_name=? LIMIT 3", (project_name,))
        for row in cursor.fetchall():
            print(f"       {row['parent_file']} failed to resolve '{row['raw_import']}' ({row['reason']})")

    # Verify node_modules
    cursor.execute("SELECT COUNT(*) as count FROM component_relationships WHERE child_file LIKE '%node_modules%'")
    nm_count = cursor.fetchone()["count"]
    print(f"\n  -> Node modules in database (Should be 0!): {nm_count}")

    conn.close()

if __name__ == "__main__":
    main()
