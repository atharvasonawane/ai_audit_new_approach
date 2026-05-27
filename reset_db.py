"""
reset_db.py
===========
Completely resets the audit database by:
1. Closing all WAL connections (checkpoint + truncate)
2. Dropping all tables
3. Deleting the WAL and SHM files
4. Re-initializing the schema from scratch

Run from the project root:
    python reset_db.py
"""

import os
import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "audit_history.db"
WAL_PATH = PROJECT_ROOT / "audit_history.db-wal"
SHM_PATH = PROJECT_ROOT / "audit_history.db-shm"

TABLES = [
    "ai_issues",
    "accessibility_defects",
    "file_flags",
    "api_calls",
    "component_relationships",
    "unresolved_imports",
    "dependency_metrics",
    "vue_files",
    "audit_runs",
]

def reset():
    print("=" * 55)
    print("  DATABASE RESET UTILITY")
    print("=" * 55)

    # Step 1: Force WAL checkpoint to avoid corruption
    if DB_PATH.exists():
        print(f"\n[1/4] Checkpointing WAL file: {DB_PATH.name} ...")
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.commit()

            # Step 2: Drop all tables (child tables first due to FK constraints)
            print("[2/4] Dropping all tables ...")
            conn.execute("PRAGMA foreign_keys=OFF;")
            for table in TABLES:
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if result:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"  Dropped: {table}")
                else:
                    print(f"  Skipped (not found): {table}")
            conn.commit()
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.close()
            print("  All tables dropped.")
        except Exception as e:
            print(f"  WARNING: Could not drop tables via connection: {e}")
            print("  Will delete the DB file directly instead.")

    # Step 3: Delete all SQLite files
    print("\n[3/4] Deleting database files ...")
    for fpath in [DB_PATH, WAL_PATH, SHM_PATH]:
        if fpath.exists():
            try:
                fpath.unlink()
                print(f"  Deleted: {fpath.name}")
            except Exception as e:
                print(f"  ERROR deleting {fpath.name}: {e}")
                sys.exit(1)
        else:
            print(f"  Not found (OK): {fpath.name}")

    # Step 4: Re-initialize fresh schema
    print("\n[4/4] Re-initializing fresh schema ...")
    try:
        # Add audit_tool/task2_audit to path so db imports work
        sys.path.insert(0, str(PROJECT_ROOT))
        sys.path.insert(1, str(PROJECT_ROOT / "audit_tool" / "task2_audit"))

        from db.db_init import init_db
        init_db(DB_PATH)
        print(f"  Schema created at: {DB_PATH}")
    except Exception as e:
        print(f"  ERROR during init_db: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Verify
    conn = sqlite3.connect(str(DB_PATH))
    tables_found = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()

    print("\n" + "=" * 55)
    print("  RESET COMPLETE — Fresh database initialized")
    print("=" * 55)
    print(f"\n  DB path  : {DB_PATH}")
    print(f"  Tables   : {', '.join(t[0] for t in tables_found)}")
    print(f"  Runs     : 0")
    print("\n  You can now run a fresh scan:")
    print("  audit_tool\\venv\\Scripts\\python.exe audit_tool\\run_audit.py")
    print()

if __name__ == "__main__":
    confirm = input("\nThis will DELETE ALL DATA in the database. Type 'yes' to confirm: ").strip()
    if confirm.lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    reset()
