"""
db/db_writer.py
───────────────────────────────────────────────────────────────
Helper functions to safely insert / upsert records into every
table in the Code Audit Librarian database.

Design decisions:
    • Every public function accepts an open sqlite3.Connection.
      The caller (scanner, AI pipeline, etc.) controls the
      connection lifecycle — this avoids opening/closing a
      connection for every row.
    • All writes are wrapped in try/except sqlite3.Error so a
      bad row never crashes the whole pipeline; errors are
      logged and the function returns None / False.
    • Upsert strategy:
        - vue_files uses INSERT OR REPLACE (full row overwrite)
          because the UNIQUE constraint on (project_name, file_path)
          makes it safe and efficient.
        - component_relationships uses INSERT OR IGNORE to avoid
          duplicates on the same edge.
        - file_flags / api_calls / ai_issues are always freshly
          inserted (callers delete old rows before re-scanning).
        - audit_runs rows are inserted once and updated in-place.

Usage:
    from db.db_init import get_connection
    from db import db_writer

    conn = get_connection()
    vue_id = db_writer.upsert_vue_file(conn, project_name="my-app", ...)
    db_writer.insert_file_flag(conn, vue_file_id=vue_id, ...)
    conn.close()
"""

import sqlite3
from typing import Any

from audit_tool.utils.logger import get_logger

logger = get_logger(__name__)


# ── Internal helper ────────────────────────────────────────────

def _execute(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    operation: str = "write",
) -> sqlite3.Cursor | None:
    """
    Execute *sql* with *params* on *conn*.

    Returns the cursor on success, or None on SQLite error.
    All errors are logged; exceptions are NOT re-raised so a
    single bad row never halts the pipeline.
    """
    try:
        cursor = conn.execute(sql, params)
        return cursor
    except sqlite3.Error as exc:
        logger.error("SQLite %s error — %s | SQL: %s | Params: %s", operation, exc, sql.strip(), params)
        return None


# ── vue_files ──────────────────────────────────────────────────

def upsert_vue_file(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
    file_hash: str,
    script_lines: int = 0,
    template_lines: int = 0,
    style_lines: int = 0,
    methods: int = 0,
    computed: int = 0,
    watchers: int = 0,
    props: int = 0,
    emits: int = 0,
    api_total: int = 0,
    api_in_mounted: int = 0,
    api_in_loop: int = 0,
    child_components: int = 0,
    max_nesting_depth: int = 0,
    cyclomatic_complexity: int = 0,
    payload_size_kb: float = 0.0,
    eslint_flag_count: int = 0,
    script_setup: bool = False,
    template_only: bool = False,
    typescript_detected: bool = False,
    last_modified: float | None = None,
) -> int | None:
    """
    Insert or fully replace a vue_files row.

    Returns the row id on success, or None on error.
    """
    sql = """
        INSERT OR REPLACE INTO vue_files (
            project_name, file_path, file_hash,
            script_lines, template_lines, style_lines,
            methods, computed, watchers, props, emits,
            api_total, api_in_mounted, api_in_loop,
            child_components, max_nesting_depth, cyclomatic_complexity,
            payload_size_kb, eslint_flag_count,
            script_setup, template_only, typescript_detected,
            last_modified, scanned_at
        ) VALUES (
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, CURRENT_TIMESTAMP
        )
    """
    params = (
        project_name, file_path, file_hash,
        script_lines, template_lines, style_lines,
        methods, computed, watchers, props, emits,
        api_total, api_in_mounted, api_in_loop,
        child_components, max_nesting_depth, cyclomatic_complexity,
        payload_size_kb, eslint_flag_count,
        int(script_setup), int(template_only), int(typescript_detected),
        last_modified,
    )
    cursor = _execute(conn, sql, params, operation="upsert vue_files")
    if cursor is not None:
        row_id = cursor.lastrowid
        logger.debug("vue_files upsert — id=%s  path=%s", row_id, file_path)
        return row_id
    return None


def get_vue_file_id(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
) -> int | None:
    """Return the id of an existing vue_files row, or None if not found."""
    cursor = _execute(
        conn,
        "SELECT id FROM vue_files WHERE project_name = ? AND file_path = ?",
        (project_name, file_path),
        operation="select vue_files",
    )
    if cursor:
        row = cursor.fetchone()
        return row["id"] if row else None
    return None


# ── file_flags ─────────────────────────────────────────────────

def insert_file_flag(
    conn: sqlite3.Connection,
    *,
    vue_file_id: int,
    project_name: str,
    file_path: str,
    rule: str | None = None,
    message: str | None = None,
    severity: str | None = None,
    line_number: int = 0,
    column_number: int = 0,
) -> int | None:
    """
    Insert a single ESLint finding into file_flags.

    Returns the new row id, or None on error.
    """
    sql = """
        INSERT INTO file_flags
            (vue_file_id, project_name, file_path,
             rule, message, severity, line_number, column_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor = _execute(
        conn, sql,
        (vue_file_id, project_name, file_path, rule, message, severity, line_number, column_number),
        operation="insert file_flags",
    )
    return cursor.lastrowid if cursor else None


def delete_file_flags(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
) -> None:
    """Remove all existing flags for a file before re-inserting fresh ones."""
    _execute(
        conn,
        "DELETE FROM file_flags WHERE project_name = ? AND file_path = ?",
        (project_name, file_path),
        operation="delete file_flags",
    )


# ── api_calls ──────────────────────────────────────────────────

def insert_api_call(
    conn: sqlite3.Connection,
    *,
    vue_file_id: int,
    project_name: str,
    file_path: str,
    api_type: str | None = None,
    method_name: str | None = None,
    endpoint: str | None = None,
    in_mounted: bool = False,
    in_loop: bool = False,
    line_number: int = 0,
) -> int | None:
    """
    Insert a detected API call into api_calls.

    Returns the new row id, or None on error.
    """
    sql = """
        INSERT INTO api_calls
            (vue_file_id, project_name, file_path,
             api_type, method_name, endpoint,
             in_mounted, in_loop, line_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor = _execute(
        conn, sql,
        (
            vue_file_id, project_name, file_path,
            api_type, method_name, endpoint,
            int(in_mounted), int(in_loop), line_number,
        ),
        operation="insert api_calls",
    )
    return cursor.lastrowid if cursor else None


def delete_api_calls(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
) -> None:
    """Remove all existing API call rows for a file before re-inserting."""
    _execute(
        conn,
        "DELETE FROM api_calls WHERE project_name = ? AND file_path = ?",
        (project_name, file_path),
        operation="delete api_calls",
    )


# ── component_relationships ────────────────────────────────────

def upsert_component_relationship(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    parent_file: str,
    child_file: str,
    relationship_type: str | None = None,
) -> int | None:
    """
    Insert a component import edge, ignoring duplicates.

    Returns the new row id (or the existing one via lastrowid on IGNORE),
    or None on error.
    """
    sql = """
        INSERT OR IGNORE INTO component_relationships
            (project_name, parent_file, child_file, relationship_type)
        VALUES (?, ?, ?, ?)
    """
    cursor = _execute(
        conn, sql,
        (project_name, parent_file, child_file, relationship_type),
        operation="upsert component_relationships",
    )
    return cursor.lastrowid if cursor else None


def delete_component_relationships(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    parent_file: str,
) -> None:
    """Remove all outgoing edges for a parent file before re-inserting."""
    _execute(
        conn,
        "DELETE FROM component_relationships WHERE project_name = ? AND parent_file = ?",
        (project_name, parent_file),
        operation="delete component_relationships",
    )


# ── ai_issues ─────────────────────────────────────────────────

def insert_ai_issue(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
    phase: str,
    issue_category: str | None = None,
    description: str | None = None,
    severity: str | None = None,
    line_number: int = 0,
    code_snippet: str | None = None,
    recommendation: str | None = None,
) -> int | None:
    """
    Insert a single LLM-identified issue into ai_issues.

    Args:
        phase: One of 'dependency', 'per_file', or 'synthesis'.

    Returns the new row id, or None on error.
    """
    sql = """
        INSERT INTO ai_issues
            (project_name, file_path, phase,
             issue_category, description, severity,
             line_number, code_snippet, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor = _execute(
        conn, sql,
        (
            project_name, file_path, phase,
            issue_category, description, severity,
            line_number, code_snippet, recommendation,
        ),
        operation="insert ai_issues",
    )
    return cursor.lastrowid if cursor else None


def delete_ai_issues_for_file(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    file_path: str,
    phase: str,
) -> None:
    """Remove existing AI issues for a file/phase so they can be re-inserted."""
    _execute(
        conn,
        "DELETE FROM ai_issues WHERE project_name = ? AND file_path = ? AND phase = ?",
        (project_name, file_path, phase),
        operation="delete ai_issues",
    )


# ── audit_runs ─────────────────────────────────────────────────

def create_audit_run(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    total_files: int = 0,
) -> int | None:
    """
    Insert a new audit_runs row and return its id.

    Status defaults to 'in_progress', phase to 'scout'.
    """
    sql = """
        INSERT INTO audit_runs
            (project_name, total_files, current_phase, status)
        VALUES (?, ?, 'scout', 'in_progress')
    """
    cursor = _execute(conn, sql, (project_name, total_files), operation="insert audit_runs")
    if cursor:
        run_id = cursor.lastrowid
        logger.info("audit_runs row created — id=%s  project=%s", run_id, project_name)
        return run_id
    return None


def update_audit_run(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    current_phase: str | None = None,
    status: str | None = None,
    completed_files: int | None = None,
    last_completed_file: str | None = None,
    synthesis_text: str | None = None,
) -> None:
    """
    Partially update an audit_runs row.

    Only non-None keyword arguments are written; all others are left as-is.
    """
    updates: list[str] = []
    params: list[Any] = []

    if current_phase is not None:
        updates.append("current_phase = ?");  params.append(current_phase)
    if status is not None:
        updates.append("status = ?");         params.append(status)
    if completed_files is not None:
        updates.append("completed_files = ?"); params.append(completed_files)
    if last_completed_file is not None:
        updates.append("last_completed_file = ?"); params.append(last_completed_file)
    if synthesis_text is not None:
        updates.append("synthesis_text = ?"); params.append(synthesis_text)
    if status == "complete":
        updates.append("completed_at = CURRENT_TIMESTAMP")

    if not updates:
        return

    sql = f"UPDATE audit_runs SET {', '.join(updates)} WHERE id = ?"
    params.append(run_id)
    _execute(conn, sql, tuple(params), operation="update audit_runs")


def get_in_progress_run(
    conn: sqlite3.Connection,
    *,
    project_name: str,
) -> sqlite3.Row | None:
    """
    Return the most recent in-progress audit run for a project, or None.

    Used by run_audit.py to offer crash recovery on startup.
    """
    cursor = _execute(
        conn,
        """
        SELECT * FROM audit_runs
        WHERE project_name = ? AND status = 'in_progress'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (project_name,),
        operation="select audit_runs",
    )
    if cursor:
        return cursor.fetchone()
    return None
