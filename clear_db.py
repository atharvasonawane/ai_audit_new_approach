"""
clear_db.py - Wipes all tables from audit_history.db for a fresh scan.
Run this AFTER closing any other process that may have the DB open.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "audit_history.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all user tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

if not tables:
    print("Database is already empty. Nothing to clear.")
else:
    print(f"Found {len(tables)} tables: {tables}")
    # Disable foreign keys to avoid constraint issues while dropping
    cursor.execute("PRAGMA foreign_keys = OFF")
    for t in tables:
        cursor.execute(f"DROP TABLE IF EXISTS [{t}]")
        print(f"  Dropped table: {t}")
    conn.commit()
    print("\n✅ All tables dropped. Database is now fresh.")

conn.close()

# Also remove WAL and SHM files
for ext in ["-shm", "-wal"]:
    p = DB_PATH + ext
    if os.path.exists(p):
        os.remove(p)
        print(f"  Removed: {p}")

print("Done! Run `run_audit.py` to start a fresh scan.")
