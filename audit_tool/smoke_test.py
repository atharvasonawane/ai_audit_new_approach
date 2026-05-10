"""
Smoke test for Stage 1 foundation files.
Run from audit_tool/ directory:  python smoke_test.py
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import audit_tool...` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── 1. Logger ──────────────────────────────────────────────────
from audit_tool.utils.logger import get_logger
logger = get_logger("smoke_test")
logger.info("Logger initialised OK")

# ── 2. DB init ─────────────────────────────────────────────────
from audit_tool.db.db_init import initialise_database, get_connection, DB_PATH
initialise_database()
logger.info("DB initialised at: %s", DB_PATH)

# ── 3. Verify all 6 tables exist ───────────────────────────────
conn = get_connection()
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row["name"] for row in cursor.fetchall()]
conn.close()

expected = {"ai_issues", "api_calls", "audit_runs", "component_relationships", "file_flags", "vue_files"}
# SQLite adds sqlite_sequence when AUTOINCREMENT is used — use subset check
missing = expected - set(tables)
assert not missing, f"Missing tables: {missing}"
logger.info("All 6 tables confirmed: %s", [t for t in tables if t in expected])

# ── 4. db_writer round-trip ────────────────────────────────────
from audit_tool.db import db_writer

conn = get_connection()
with conn:
    run_id = db_writer.create_audit_run(conn, project_name="smoke-test", total_files=5)
    assert run_id is not None, "create_audit_run returned None"

    vue_id = db_writer.upsert_vue_file(
        conn,
        project_name="smoke-test",
        file_path="src/components/Test.vue",
        file_hash="abc123",
        script_lines=50,
        methods=3,
    )
    assert vue_id is not None, "upsert_vue_file returned None"

    flag_id = db_writer.insert_file_flag(
        conn,
        vue_file_id=vue_id,
        project_name="smoke-test",
        file_path="src/components/Test.vue",
        rule="vue/no-unused-vars",
        message="unused variable x",
        severity="warn",
        line_number=12,
    )
    assert flag_id is not None, "insert_file_flag returned None"

    api_id = db_writer.insert_api_call(
        conn,
        vue_file_id=vue_id,
        project_name="smoke-test",
        file_path="src/components/Test.vue",
        api_type="axios",
        method_name="fetchUser",
        in_mounted=True,
        line_number=30,
    )
    assert api_id is not None, "insert_api_call returned None"

    rel_id = db_writer.upsert_component_relationship(
        conn,
        project_name="smoke-test",
        parent_file="src/App.vue",
        child_file="src/components/Test.vue",
        relationship_type="import",
    )
    assert rel_id is not None, "upsert_component_relationship returned None"

    issue_id = db_writer.insert_ai_issue(
        conn,
        project_name="smoke-test",
        file_path="src/components/Test.vue",
        phase="per_file",
        issue_category="State Management Bloat",
        description="Too much state in data()",
        severity="High",
        line_number=20,
        recommendation="Move to Pinia store",
    )
    assert issue_id is not None, "insert_ai_issue returned None"

    db_writer.update_audit_run(
        conn,
        run_id=run_id,
        current_phase="ai",
        completed_files=5,
        status="complete",
    )

conn.close()

logger.info(
    "db_writer round-trip OK — vue_id=%s  flag_id=%s  api_id=%s  rel_id=%s  issue_id=%s  run_id=%s",
    vue_id, flag_id, api_id, rel_id, issue_id, run_id,
)

print()
print("=== ALL SMOKE TESTS PASSED ===")
