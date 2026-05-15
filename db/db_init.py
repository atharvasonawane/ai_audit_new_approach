import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "audit_history.db"


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")


def init_db(db_path: Optional[Path] = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        _apply_pragmas(conn)
        _create_tables(conn)

    return path


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vue_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE(project_name, file_path)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accessibility_defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS component_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            parent_file TEXT,
            child_file TEXT,
            relationship_type TEXT,
            UNIQUE(project_name, parent_file, child_file)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            started_at TEXT,
            status TEXT,
            last_completed_file TEXT,
            synthesis_text TEXT,
            completed_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS unresolved_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            parent_file TEXT NOT NULL,
            raw_import TEXT NOT NULL,
            reason TEXT,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dependency_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE(project_name, file_path)
        )
        """
    )
