import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from db.db_init import DEFAULT_DB_PATH


def _get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _normalize_path(file_path: str, base_path: str) -> str:
    if base_path:
        try:
            from extractors.path_utils import normalize_path

            return normalize_path(file_path, base_path)
        except Exception:
            pass

    return file_path.replace("\\", "/")


def calculate_file_hash(filepath: str) -> str:
    import hashlib

    try:
        with open(filepath, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except Exception:
        return ""


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


def get_all_file_hashes(
    project_name: str, db_path: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    sql = (
        "SELECT file_path, file_hash, scanned_at FROM vue_files WHERE project_name = ?"
    )
    results: Dict[str, Dict[str, Any]] = {}

    with _get_connection(db_path) as conn:
        for row in conn.execute(sql, (project_name,)):
            scanned_at = row["scanned_at"]
            scanned_dt = None
            if scanned_at:
                try:
                    scanned_dt = datetime.fromisoformat(scanned_at)
                except ValueError:
                    scanned_dt = None

            if row["file_hash"]:
                results[row["file_path"]] = {
                    "hash": row["file_hash"],
                    "scanned_at": scanned_dt,
                }

    return results


def write_scan_result(
    project_name: str,
    cfg: Dict[str, Any],
    result: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> int:
    metrics = result.get("extracted_metrics", {})
    api_calls = result.get("api_calls", [])
    file_path = result.get("file", "")
    base_path = cfg.get("base_path", "") if cfg else ""
    normalized_path = _normalize_path(file_path, base_path)
    scanned_at = datetime.utcnow().isoformat()
    last_modified = None

    try:
        last_modified = os.path.getmtime(file_path)
    except OSError:
        last_modified = None

    api_in_loop = sum(1 for call in api_calls if call.get("in_loop"))

    vue_file_id = upsert_vue_file(
        {
            "project_name": project_name,
            "file_path": normalized_path,
            "file_hash": result.get("file_hash", ""),
            "script_lines": metrics.get("script_lines", 0),
            "template_lines": metrics.get("template_lines", 0),
            "style_lines": metrics.get("style_lines", 0),
            "methods": metrics.get("methods", 0),
            "computed": metrics.get("computed", 0),
            "watchers": metrics.get("watchers", 0),
            "props": metrics.get("props", 0),
            "emits": metrics.get("emits", 0),
            "api_total": metrics.get("api_total", 0),
            "api_in_mounted": metrics.get("api_in_mounted", 0),
            "api_in_loop": api_in_loop,
            "child_components": metrics.get("child_components", 0),
            "max_nesting_depth": metrics.get("max_nest_depth", 0),
            "cyclomatic_complexity": metrics.get("cyclomatic_complexity", 0),
            "payload_size_kb": metrics.get("payload_size_kb", 0.0),
            "eslint_flag_count": metrics.get("eslint_flag_count", 0),
            "script_setup": metrics.get("script_setup", 0),
            "template_only": metrics.get("template_only", 0),
            "typescript_detected": metrics.get("typescript_detected", 0),
            "last_modified": last_modified,
            "scanned_at": scanned_at,
        },
        db_path=db_path,
    )

    with _get_connection(db_path) as conn:
        conn.execute("DELETE FROM api_calls WHERE vue_file_id = ?", (vue_file_id,))

        for call in api_calls:
            conn.execute(
                """
                INSERT INTO api_calls
                    (vue_file_id, project_name, file_path, api_type, method_name, endpoint, in_mounted, in_loop, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vue_file_id,
                    project_name,
                    normalized_path,
                    call.get("type"),
                    call.get("method"),
                    call.get("full_match"),
                    1 if call.get("in_mounted") else 0,
                    1 if call.get("in_loop") else 0,
                    call.get("line_number", 0),
                ),
            )

        conn.commit()

    return vue_file_id


def write_eslint_results(
    project_name: str,
    cfg: Dict[str, Any],
    eslint_results: Iterable[Dict[str, Any]],
    db_path: Optional[Path] = None,
) -> Dict[str, int]:
    if not eslint_results:
        return {"file_flags": 0, "accessibility_defects": 0}

    base_path = cfg.get("base_path", "") if cfg else ""
    file_flags_written = 0
    accessibility_written = 0
    touched_files = set()

    with _get_connection(db_path) as conn:
        for entry in eslint_results:
            normalized_path = _normalize_path(entry.get("file_path", ""), base_path)
            row = conn.execute(
                "SELECT id FROM vue_files WHERE project_name = ? AND file_path = ?",
                (project_name, normalized_path),
            ).fetchone()
            if not row:
                continue

            vue_file_id = row["id"]

            if vue_file_id not in touched_files:
                conn.execute(
                    "DELETE FROM file_flags WHERE vue_file_id = ?", (vue_file_id,)
                )
                conn.execute(
                    "DELETE FROM accessibility_defects WHERE vue_file_id = ?",
                    (vue_file_id,),
                )
                touched_files.add(vue_file_id)

            rule_id = entry.get("rule_id", "") or ""
            is_accessibility = rule_id.startswith("vuejs-accessibility")
            severity = "error" if entry.get("severity", 0) >= 2 else "warning"

            if is_accessibility:
                conn.execute(
                    """
                    INSERT INTO accessibility_defects
                        (vue_file_id, project_name, file_path, rule, message, wcag_criterion, wcag_level, line_number, column_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vue_file_id,
                        project_name,
                        normalized_path,
                        rule_id,
                        entry.get("message", ""),
                        "",
                        "",
                        entry.get("line", 0),
                        entry.get("column", 0),
                    ),
                )
                accessibility_written += 1
            else:
                conn.execute(
                    """
                    INSERT INTO file_flags
                        (vue_file_id, project_name, file_path, category, rule, message, severity, line_number, column_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vue_file_id,
                        project_name,
                        normalized_path,
                        "eslint",
                        rule_id,
                        entry.get("message", ""),
                        severity,
                        entry.get("line", 0),
                        entry.get("column", 0),
                    ),
                )
                file_flags_written += 1

        conn.commit()

    return {
        "file_flags": file_flags_written,
        "accessibility_defects": accessibility_written,
    }


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
