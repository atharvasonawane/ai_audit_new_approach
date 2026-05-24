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
    # Sync WAL to main DB file after each write so all readers (browser, file viewers)
    # see the latest data. Without this, changes only exist in the .db-wal sidecar file.
    conn.execute("PRAGMA wal_autocheckpoint=1;")  # checkpoint after every 1 page change
    return conn


def _checkpoint(conn: sqlite3.Connection) -> None:
    """Force WAL checkpoint so the main .db file is updated on disk immediately.
    
    SQLite WAL mode buffers writes in audit_history.db-wal. Without an explicit
    checkpoint, the main .db file timestamp never updates and non-WAL-aware readers
    (web browsers, third-party SQLite viewers) see stale data.
    """
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
    except Exception:
        pass  # Non-critical — data is safe in WAL even if checkpoint fails

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

def create_audit_run(project_name: str, db_path: Optional[Path] = None) -> int:
    with _get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO audit_runs (project_name, started_at, status) VALUES (?, datetime('now'), 'in_progress')",
            (project_name,)
        )
        new_run_id = cur.lastrowid
        
        # Copy data from the previous completed run
        prev_run = conn.execute(
            "SELECT id FROM audit_runs WHERE project_name = ? AND status = 'completed' ORDER BY started_at DESC LIMIT 1",
            (project_name,)
        ).fetchone()
        
        if prev_run:
            prev_id = prev_run["id"]
            
            # Copy vue_files
            conn.execute(f"""
                INSERT INTO vue_files (run_id, project_name, file_path, file_hash, script_lines, template_lines, style_lines, methods, computed, watchers, props, emits, api_total, api_in_mounted, api_in_loop, child_components, max_nesting_depth, cyclomatic_complexity, payload_size_kb, eslint_flag_count, script_setup, template_only, typescript_detected, last_modified, scanned_at)
                SELECT ?, project_name, file_path, file_hash, script_lines, template_lines, style_lines, methods, computed, watchers, props, emits, api_total, api_in_mounted, api_in_loop, child_components, max_nesting_depth, cyclomatic_complexity, payload_size_kb, eslint_flag_count, script_setup, template_only, typescript_detected, last_modified, scanned_at
                FROM vue_files WHERE run_id = ?
            """, (new_run_id, prev_id))
            
            # api_calls
            conn.execute(f"""
                INSERT INTO api_calls (run_id, vue_file_id, project_name, file_path, api_type, method_name, endpoint, in_mounted, in_loop, line_number)
                SELECT ?, nv.id, o.project_name, o.file_path, o.api_type, o.method_name, o.endpoint, o.in_mounted, o.in_loop, o.line_number
                FROM api_calls o
                JOIN vue_files ov ON o.vue_file_id = ov.id
                JOIN vue_files nv ON nv.run_id = ? AND nv.file_path = ov.file_path
                WHERE o.run_id = ?
            """, (new_run_id, new_run_id, prev_id))
            
            # file_flags
            conn.execute(f"""
                INSERT INTO file_flags (run_id, vue_file_id, project_name, file_path, category, rule, message, severity, line_number, column_number)
                SELECT ?, nv.id, o.project_name, o.file_path, o.category, o.rule, o.message, o.severity, o.line_number, o.column_number
                FROM file_flags o
                JOIN vue_files ov ON o.vue_file_id = ov.id
                JOIN vue_files nv ON nv.run_id = ? AND nv.file_path = ov.file_path
                WHERE o.run_id = ?
            """, (new_run_id, new_run_id, prev_id))
            
            # accessibility_defects
            conn.execute(f"""
                INSERT INTO accessibility_defects (run_id, vue_file_id, project_name, file_path, rule, message, wcag_criterion, wcag_level, line_number, column_number)
                SELECT ?, nv.id, o.project_name, o.file_path, o.rule, o.message, o.wcag_criterion, o.wcag_level, o.line_number, o.column_number
                FROM accessibility_defects o
                JOIN vue_files ov ON o.vue_file_id = ov.id
                JOIN vue_files nv ON nv.run_id = ? AND nv.file_path = ov.file_path
                WHERE o.run_id = ?
            """, (new_run_id, new_run_id, prev_id))
            
            # ai_issues
            conn.execute(f"""
                INSERT INTO ai_issues (run_id, vue_file_id, project_name, file_path, phase, issue_category, title, description, severity, line_number, code_snippet, recommendation, created_at)
                SELECT ?, nv.id, o.project_name, o.file_path, o.phase, o.issue_category, o.title, o.description, o.severity, o.line_number, o.code_snippet, o.recommendation, o.created_at
                FROM ai_issues o
                JOIN vue_files ov ON o.vue_file_id = ov.id
                JOIN vue_files nv ON nv.run_id = ? AND nv.file_path = ov.file_path
                WHERE o.run_id = ?
            """, (new_run_id, new_run_id, prev_id))
            
            # component_relationships
            conn.execute(f"""
                INSERT INTO component_relationships (run_id, project_name, parent_file, child_file, relationship_type)
                SELECT ?, project_name, parent_file, child_file, relationship_type
                FROM component_relationships WHERE run_id = ?
            """, (new_run_id, prev_id))

            # unresolved_imports
            conn.execute(f"""
                INSERT INTO unresolved_imports (run_id, project_name, parent_file, raw_import, reason, scanned_at)
                SELECT ?, project_name, parent_file, raw_import, reason, scanned_at
                FROM unresolved_imports WHERE run_id = ?
            """, (new_run_id, prev_id))

            # dependency_metrics
            conn.execute(f"""
                INSERT INTO dependency_metrics (run_id, project_name, file_path, in_degree, out_degree, depth, impact_score, node_category, is_in_cycle, cycle_members, dependents, dependencies)
                SELECT ?, project_name, file_path, in_degree, out_degree, depth, impact_score, node_category, is_in_cycle, cycle_members, dependents, dependencies
                FROM dependency_metrics WHERE run_id = ?
            """, (new_run_id, prev_id))
            
        conn.commit()
        _checkpoint(conn)
        return new_run_id

def update_audit_run(
    run_id: int, 
    status: Optional[str] = None, 
    last_completed_file: Optional[str] = None,
    total_files: Optional[int] = None, 
    synthesis_text: Optional[str] = None, 
    completed: bool = False,
    db_path: Optional[Path] = None
) -> None:
    fields, params = [], []
    if status:                   
        fields.append("status = ?")
        params.append(status)
    if last_completed_file:      
        fields.append("last_completed_file = ?")
        params.append(last_completed_file)
    if total_files is not None:  
        fields.append("total_files = ?")
        params.append(total_files)
    if synthesis_text:           
        fields.append("synthesis_text = ?")
        params.append(synthesis_text)
    if completed:
        fields += ["status = 'completed'", "completed_at = datetime('now')"]
        
    if not fields: return
    params.append(run_id)
    
    with _get_connection(db_path) as conn:
        conn.execute(f"UPDATE audit_runs SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        _checkpoint(conn)

def upsert_vue_file(run_id: int, data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    columns = [
        "run_id",
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

    data["run_id"] = run_id
    values = [data.get(col) for col in columns]

    set_clause = ", ".join([f"{col}=excluded.{col}" for col in columns if col not in ["run_id", "project_name", "file_path"]])

    sql = f"""
        INSERT INTO vue_files ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
        ON CONFLICT(run_id, project_name, file_path) DO UPDATE SET
        {set_clause}
    """

    with _get_connection(db_path) as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        _checkpoint(conn)
        row_id = cur.lastrowid

        if not row_id:
            row = conn.execute(
                "SELECT id FROM vue_files WHERE run_id = ? AND project_name = ? AND file_path = ?",
                (run_id, data.get("project_name"), data.get("file_path")),
            ).fetchone()
            if row:
                row_id = row["id"]

    return int(row_id)

def upsert_component_relationship(
    run_id: int, data: Dict[str, Any], db_path: Optional[Path] = None
) -> int:
    columns = ["run_id", "project_name", "parent_file", "child_file", "relationship_type"]
    data["run_id"] = run_id
    values = [data.get(col) for col in columns]

    sql = f"""
        INSERT INTO component_relationships ({", ".join(columns)})
        VALUES ({", ".join(["?"] * len(columns))})
        ON CONFLICT(run_id, project_name, parent_file, child_file) DO UPDATE SET
        relationship_type=excluded.relationship_type
    """

    with _get_connection(db_path) as conn:
        cur = conn.execute(sql, values)
        conn.commit()
        return int(cur.lastrowid or 0)

def insert_ai_issues_bulk(run_id: int, issues: list[dict], db_path: Optional[Path] = None):
    with _get_connection(db_path) as conn:
        for i in issues:
            conn.execute(
                """
                INSERT INTO ai_issues 
                  (run_id, vue_file_id, project_name, file_path, phase, issue_category, 
                   title, description, severity, line_number, code_snippet, recommendation) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, i.get("vue_file_id"), i.get("project_name"), i.get("file_path"),
                    i.get("phase"), i.get("issue_category"), i.get("title"), i.get("description"),
                    i.get("severity"), i.get("line_number"), i.get("code_snippet"), i.get("recommendation")
                )
            )
        conn.commit()
        _checkpoint(conn)

def get_all_file_hashes(
    project_name: str, run_id: Optional[int] = None, db_path: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    with _get_connection(db_path) as conn:
        if run_id is None:
            # Fall back to latest run
            run_row = conn.execute("SELECT id FROM audit_runs WHERE project_name = ? AND status = 'completed' ORDER BY started_at DESC LIMIT 1", (project_name,)).fetchone()
            if not run_row:
                return results
            run_id_val = run_row["id"]
        else:
            run_id_val = run_id
            
        sql = "SELECT file_path, file_hash, scanned_at FROM vue_files WHERE run_id = ? AND project_name = ?"
        for row in conn.execute(sql, (run_id_val, project_name)):
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
    run_id: int,
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
        run_id,
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
        # Since vue_file_id is unique per run, this clears out the old duplicated data
        conn.execute("DELETE FROM api_calls WHERE vue_file_id = ?", (vue_file_id,))

        for call in api_calls:
            conn.execute(
                """
                INSERT INTO api_calls
                    (run_id, vue_file_id, project_name, file_path, api_type, method_name, endpoint, in_mounted, in_loop, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
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
        _checkpoint(conn)

    return vue_file_id

def write_eslint_results(
    run_id: int,
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
                "SELECT id FROM vue_files WHERE run_id = ? AND project_name = ? AND file_path = ?",
                (run_id, project_name, normalized_path),
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
                        (run_id, vue_file_id, project_name, file_path, rule, message, wcag_criterion, wcag_level, line_number, column_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
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
                        (run_id, vue_file_id, project_name, file_path, category, rule, message, severity, line_number, column_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
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

        # Update eslint_flag_count in vue_files for all touched files
        for vue_file_id in touched_files:
            flag_count_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM file_flags
                WHERE vue_file_id = ? AND category = 'eslint'
                """,
                (vue_file_id,),
            ).fetchone()
            flag_count = flag_count_row["cnt"] if flag_count_row else 0
            
            conn.execute(
                "UPDATE vue_files SET eslint_flag_count = ? WHERE id = ?",
                (flag_count, vue_file_id),
            )
        
        conn.commit()
        _checkpoint(conn)

    return {
        "file_flags": file_flags_written,
        "accessibility_defects": accessibility_written,
    }

def _upsert_by_id(table: str, run_id: int, data: Dict[str, Any], db_path: Optional[Path]) -> int:
    if not data:
        raise ValueError("data is required")

    data["run_id"] = run_id
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
