import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "audit_history.db"

def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

def init_db(db_path: Optional[Path] = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        _migrate_existing_schema(conn)
        _create_tables(conn)
        _create_indexes(conn)

    return path

def _migrate_existing_schema(conn: sqlite3.Connection) -> None:
    # Migrate audit_runs to have total_files if missing
    ar_check = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_runs'").fetchone()
    if ar_check:
        ar_cols = [r["name"] for r in conn.execute("PRAGMA table_info(audit_runs)").fetchall()]
        if "total_files" not in ar_cols:
            conn.execute("ALTER TABLE audit_runs ADD COLUMN total_files INTEGER")
            conn.commit()

    tbl_check = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vue_files'").fetchone()
    if not tbl_check:
        return
        
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(vue_files)").fetchall()]
    if "run_id" in cols:
        return
        
    logger.info("Migrating database to include run_id and update constraints...")
    conn.execute("PRAGMA foreign_keys=OFF;")
    
    row = conn.execute("SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if row:
        fallback_run_id = row["id"]
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT,
                started_at TEXT,
                status TEXT,
                last_completed_file TEXT,
                total_files INTEGER,
                synthesis_text TEXT,
                completed_at TEXT
            )
            """
        )
        cur = conn.execute(
            "INSERT INTO audit_runs (project_name, started_at, status) VALUES ('__migrated__', datetime('now'), 'completed')"
        )
        fallback_run_id = cur.lastrowid

    tables_to_migrate = [
        "vue_files", "api_calls", "file_flags", "accessibility_defects",
        "component_relationships", "ai_issues", "unresolved_imports", "dependency_metrics"
    ]

    for table in tables_to_migrate:
        if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            continue
            
        old_cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "run_id" in old_cols:
            continue
            
        logger.info(f"Migrating table {table}...")
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
        _create_tables(conn, specific_table=table)
        cols_str = ", ".join(old_cols)
        conn.execute(f"INSERT INTO {table} (run_id, {cols_str}) SELECT ?, {cols_str} FROM {table}_old", (fallback_run_id,))
        conn.execute(f"DROP TABLE {table}_old")

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON;")
    logger.info("Migration complete.")

def _create_tables(conn: sqlite3.Connection, specific_table: Optional[str] = None) -> None:
    tables = {
        "audit_runs": """
            CREATE TABLE IF NOT EXISTS audit_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT,
                started_at TEXT,
                status TEXT,
                last_completed_file TEXT,
                total_files INTEGER,
                synthesis_text TEXT,
                completed_at TEXT
            )
        """,
        "vue_files": """
            CREATE TABLE IF NOT EXISTS vue_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                project_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                script_lines INTEGER,
                template_lines INTEGER,
                style_lines INTEGER,
                methods INTEGER,
                computed INTEGER,
                watchers INTEGER,
                props INTEGER,
                emits INTEGER,
                api_total INTEGER,
                api_in_mounted INTEGER,
                api_in_loop INTEGER,
                child_components INTEGER,
                max_nesting_depth INTEGER,
                cyclomatic_complexity INTEGER,
                payload_size_kb REAL,
                eslint_flag_count INTEGER,
                script_setup INTEGER,
                template_only INTEGER,
                typescript_detected INTEGER,
                last_modified REAL,
                scanned_at TEXT,
                UNIQUE(run_id, project_name, file_path)
            )
        """,
        "api_calls": """
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                vue_file_id INTEGER,
                project_name TEXT,
                file_path TEXT,
                api_type TEXT,
                method_name TEXT,
                endpoint TEXT,
                in_mounted INTEGER,
                in_loop INTEGER,
                line_number INTEGER,
                FOREIGN KEY(vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
            )
        """,
        "file_flags": """
            CREATE TABLE IF NOT EXISTS file_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                vue_file_id INTEGER,
                project_name TEXT,
                file_path TEXT,
                category TEXT,
                rule TEXT,
                message TEXT,
                severity TEXT,
                line_number INTEGER,
                column_number INTEGER,
                FOREIGN KEY(vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
            )
        """,
        "accessibility_defects": """
            CREATE TABLE IF NOT EXISTS accessibility_defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                vue_file_id INTEGER,
                project_name TEXT,
                file_path TEXT,
                rule TEXT,
                message TEXT,
                wcag_criterion TEXT,
                wcag_level TEXT,
                line_number INTEGER,
                column_number INTEGER,
                FOREIGN KEY(vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
            )
        """,
        "component_relationships": """
            CREATE TABLE IF NOT EXISTS component_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                project_name TEXT,
                parent_file TEXT,
                child_file TEXT,
                relationship_type TEXT,
                UNIQUE(run_id, project_name, parent_file, child_file)
            )
        """,
        "ai_issues": """
            CREATE TABLE IF NOT EXISTS ai_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                vue_file_id INTEGER,
                project_name TEXT,
                file_path TEXT,
                phase TEXT,
                issue_category TEXT,
                title TEXT,
                description TEXT,
                severity TEXT,
                line_number INTEGER,
                code_snippet TEXT,
                recommendation TEXT,
                created_at TEXT,
                FOREIGN KEY(vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
            )
        """,
        "unresolved_imports": """
            CREATE TABLE IF NOT EXISTS unresolved_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                project_name TEXT NOT NULL,
                parent_file TEXT NOT NULL,
                raw_import TEXT NOT NULL,
                reason TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "dependency_metrics": """
            CREATE TABLE IF NOT EXISTS dependency_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                project_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                in_degree INTEGER DEFAULT 0,
                out_degree INTEGER DEFAULT 0,
                depth INTEGER DEFAULT 0,
                impact_score REAL DEFAULT 0,
                node_category TEXT DEFAULT 'standard',
                is_in_cycle INTEGER DEFAULT 0,
                cycle_members TEXT,
                dependents TEXT,
                dependencies TEXT,
                UNIQUE(run_id, project_name, file_path)
            )
        """
    }

    if specific_table:
        if specific_table in tables:
            conn.execute(tables[specific_table])
    else:
        for sql in tables.values():
            conn.execute(sql)

def _create_indexes(conn: sqlite3.Connection) -> None:
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_vue_files_run_id        ON vue_files(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_file_flags_run_id       ON file_flags(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_accessibility_run_id    ON accessibility_defects(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_api_calls_run_id        ON api_calls(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_ai_issues_run_id        ON ai_issues(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_comp_rel_run_id         ON component_relationships(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_unresolved_run_id       ON unresolved_imports(run_id);",
        "CREATE INDEX IF NOT EXISTS idx_dep_metrics_run_id      ON dependency_metrics(run_id);"
    ]
    for idx in indexes:
        conn.execute(idx)
