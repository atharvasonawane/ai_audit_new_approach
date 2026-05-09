"""
db/db_init.py
───────────────────────────────────────────────────────────────
Database initialiser for the Code Audit Librarian.

Responsibilities:
    • Open (or create) audit_history.db
    • Enable WAL journal mode and foreign-key enforcement
    • Create all six schema tables with CREATE TABLE IF NOT EXISTS

Usage:
    from db.db_init import initialise_database
    initialise_database()          # called once at startup by run_audit.py

Or run directly to bootstrap the DB:
    python -m db.db_init
"""

import sqlite3
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Paths ──────────────────────────────────────────────────────
# audit_tool/audit_history.db  (same directory as this package's parent)
DB_PATH = Path(__file__).resolve().parent.parent / "audit_history.db"

# ── Schema definitions ─────────────────────────────────────────
_PRAGMA_STATEMENTS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA foreign_keys=ON;",
]

_CREATE_TABLES = [

    # ── 1. vue_files ──────────────────────────────────────────
    # One row per (project, file).  Stores Scout structural facts.
    """
    CREATE TABLE IF NOT EXISTS vue_files (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name            TEXT    NOT NULL,
        file_path               TEXT    NOT NULL,
        file_hash               TEXT    NOT NULL,
        script_lines            INTEGER DEFAULT 0,
        template_lines          INTEGER DEFAULT 0,
        style_lines             INTEGER DEFAULT 0,
        methods                 INTEGER DEFAULT 0,
        computed                INTEGER DEFAULT 0,
        watchers                INTEGER DEFAULT 0,
        props                   INTEGER DEFAULT 0,
        emits                   INTEGER DEFAULT 0,
        api_total               INTEGER DEFAULT 0,
        api_in_mounted          INTEGER DEFAULT 0,
        api_in_loop             INTEGER DEFAULT 0,
        child_components        INTEGER DEFAULT 0,
        max_nesting_depth       INTEGER DEFAULT 0,
        cyclomatic_complexity   INTEGER DEFAULT 0,
        payload_size_kb         REAL    DEFAULT 0,
        eslint_flag_count       INTEGER DEFAULT 0,
        script_setup            BOOLEAN DEFAULT 0,
        template_only           BOOLEAN DEFAULT 0,
        typescript_detected     BOOLEAN DEFAULT 0,
        last_modified           REAL,
        scanned_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_name, file_path)
    );
    """,

    # ── 2. file_flags ─────────────────────────────────────────
    # ESLint findings per file.  Foreign key → vue_files.
    """
    CREATE TABLE IF NOT EXISTS file_flags (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        vue_file_id     INTEGER NOT NULL,
        project_name    TEXT    NOT NULL,
        file_path       TEXT    NOT NULL,
        rule            TEXT,
        message         TEXT,
        severity        TEXT,
        line_number     INTEGER DEFAULT 0,
        column_number   INTEGER DEFAULT 0,
        FOREIGN KEY (vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    );
    """,

    # ── 3. api_calls ──────────────────────────────────────────
    # Every API call detected per file.  Foreign key → vue_files.
    """
    CREATE TABLE IF NOT EXISTS api_calls (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        vue_file_id     INTEGER NOT NULL,
        project_name    TEXT    NOT NULL,
        file_path       TEXT    NOT NULL,
        api_type        TEXT,
        method_name     TEXT,
        endpoint        TEXT,
        in_mounted      BOOLEAN DEFAULT 0,
        in_loop         BOOLEAN DEFAULT 0,
        line_number     INTEGER DEFAULT 0,
        FOREIGN KEY (vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    );
    """,

    # ── 4. component_relationships ────────────────────────────
    # Import graph: who imports whom.  One row per unique edge.
    """
    CREATE TABLE IF NOT EXISTS component_relationships (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name        TEXT NOT NULL,
        parent_file         TEXT NOT NULL,
        child_file          TEXT NOT NULL,
        relationship_type   TEXT,
        UNIQUE(project_name, parent_file, child_file)
    );
    """,

    # ── 5. ai_issues ─────────────────────────────────────────
    # All LLM-identified issues from the three AI pipeline phases.
    """
    CREATE TABLE IF NOT EXISTS ai_issues (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name    TEXT NOT NULL,
        file_path       TEXT NOT NULL,
        phase           TEXT NOT NULL,
        issue_category  TEXT,
        description     TEXT,
        severity        TEXT CHECK(severity IN ('High', 'Medium', 'Low')),
        line_number     INTEGER DEFAULT 0,
        code_snippet    TEXT,
        recommendation  TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── 6. audit_runs ─────────────────────────────────────────
    # Tracks run state for crash recovery and progress display.
    """
    CREATE TABLE IF NOT EXISTS audit_runs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name        TEXT    NOT NULL,
        current_phase       TEXT    DEFAULT 'scout',
        status              TEXT    DEFAULT 'in_progress',
        last_completed_file TEXT,
        total_files         INTEGER DEFAULT 0,
        completed_files     INTEGER DEFAULT 0,
        synthesis_text      TEXT,
        started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at        TIMESTAMP
    );
    """,
]


# ── Public API ─────────────────────────────────────────────────

def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Return a sqlite3.Connection with WAL mode and foreign keys enabled.

    Args:
        db_path: Override the default DB path (mainly for tests).

    Returns:
        An open sqlite3.Connection.  The caller is responsible for
        closing it (or use as a context manager for transactions).
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row          # access columns by name

    # Apply pragmas immediately after opening
    for pragma in _PRAGMA_STATEMENTS:
        conn.execute(pragma)

    return conn


def initialise_database(db_path: Path | None = None) -> None:
    """
    Create the database and all schema tables if they don't already exist.

    Safe to call on every startup — all statements use IF NOT EXISTS.

    Args:
        db_path: Override the default DB path (mainly for tests).
    """
    path = db_path or DB_PATH
    logger.info("Initialising database at: %s", path)

    try:
        conn = get_connection(path)
        with conn:                          # transaction for table creation
            for stmt in _CREATE_TABLES:
                conn.execute(stmt)
        conn.close()
        logger.info("Database initialisation complete — 6 tables ready.")
    except sqlite3.Error as exc:
        logger.error("Failed to initialise database: %s", exc)
        raise


# ── CLI entry point ────────────────────────────────────────────
if __name__ == "__main__":
    initialise_database()
