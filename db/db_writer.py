import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from db.db_init import DEFAULT_DB_PATH


def _get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def upsert_vue_file(data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    columns = [
        "project_name",
        "file_path",
        "file_hash",
        "script_lines",
        "template_lines",
        "style_lines",
        "methods",
        "computed",
        "watchers",
        "props",
        "emits",
        "api_total",
        "api_in_mounted",
        "api_in_loop",
        "child_components",
        "max_nesting_depth",
        "cyclomatic_complexity",
        "payload_size_kb",
        "eslint_flag_count",
        "script_setup",
        "template_only",
        "typescript_detected",
        "last_modified",
        "scanned_at",
    ]

    values = [data.get(col) for col in columns]

    set_clause = ", ".join([f"{col}=excluded.{col}" for col in columns[2:]])

    sql = f"""
        INSERT INTO vue_files ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
        ON CONFLICT(project_name, file_path) DO UPDATE SET
        {set_clause}
    """

    with _get_connection(db_path) as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        row_id = cur.lastrowid

        if not row_id:
            row = conn.execute(
                "SELECT id FROM vue_files WHERE project_name = ? AND file_path = ?",
                (data.get("project_name"), data.get("file_path")),
            ).fetchone()
            if row:
                row_id = row["id"]

    return int(row_id)


def upsert_api_call(data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    return _upsert_by_id("api_calls", data, db_path)


def upsert_file_flag(data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    return _upsert_by_id("file_flags", data, db_path)


def upsert_accessibility_defect(
    data: Dict[str, Any], db_path: Optional[Path] = None
) -> int:
    return _upsert_by_id("accessibility_defects", data, db_path)


def upsert_component_relationship(
    data: Dict[str, Any], db_path: Optional[Path] = None
) -> int:
    columns = ["project_name", "parent_file", "child_file", "relationship_type"]
    values = [data.get(col) for col in columns]

    sql = f"""
        INSERT INTO component_relationships ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
        ON CONFLICT(project_name, parent_file, child_file) DO UPDATE SET
        relationship_type=excluded.relationship_type
    """

    with _get_connection(db_path) as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        return int(cur.lastrowid or 0)


def upsert_ai_issue(data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    return _upsert_by_id("ai_issues", data, db_path)


def upsert_audit_run(data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    return _upsert_by_id("audit_runs", data, db_path)


def _upsert_by_id(table: str, data: Dict[str, Any], db_path: Optional[Path]) -> int:
    if not data:
        raise ValueError("data is required")

    columns = list(data.keys())
    values = [data.get(col) for col in columns]

    sql = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
        ON CONFLICT(id) DO UPDATE SET
        {", ".join([f"{col}=excluded.{col}" for col in columns if col != "id"])}
    """

    with _get_connection(db_path) as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        return int(cur.lastrowid or 0)
