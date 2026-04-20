"""
audit_tool_v4/db/db_loader.py
==============================
V4 MySQL ingestion layer.

SAFETY GUARANTEE:
  - This file ONLY creates and writes to two NEW tables:
      v4_scan_runs    — one row per pipeline execution
      v4_sarif_results — one row per SARIFResult finding
  - It uses CREATE TABLE IF NOT EXISTS exclusively.
  - It NEVER touches, truncates, or modifies any existing table
    (vue_files, api_calls, file_flags, ui_extractions, ui_defects,
     accessibility_defects, rule_violations, components, metrics, etc.)
  - It connects to the same 'code_audit_db' database as db_writer.py
    but operates in a completely isolated table namespace prefixed 'v4_'.

Input contract:
  - Accepts ONLY a SARIFReport Pydantic object.
  - Never accepts raw dicts, taskX JSON, or legacy formats.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import mysql.connector

# Import the Pydantic models — path resolves because run_audit.py adds
# audit_tool_v4/ to sys.path before importing this module.
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema_models import SARIFReport, SARIFResult, Severity, Category

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DDL — V4-exclusive tables only
# ─────────────────────────────────────────────────────────────────────────────

_V4_DDL = [
    """
    CREATE TABLE IF NOT EXISTS v4_scan_runs (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        project       VARCHAR(255)       NOT NULL,
        base_path     VARCHAR(1024)      NOT NULL,
        scanned_at    DATETIME           NOT NULL,
        total_findings INT               DEFAULT 0,
        errors_count  INT                DEFAULT 0,
        warnings_count INT               DEFAULT 0,
        info_count    INT                DEFAULT 0,
        health_score  DECIMAL(5, 2)      DEFAULT 100.00,
        INDEX idx_v4_runs_project (project),
        INDEX idx_v4_runs_scanned_at (scanned_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='V4 pipeline scan run registry'
    """,
    """
    CREATE TABLE IF NOT EXISTS v4_sarif_results (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        scan_run_id   INT           NOT NULL,
        tool_name     VARCHAR(100)  NOT NULL,
        rule_id       VARCHAR(255)  NOT NULL,
        severity      ENUM('error', 'warning', 'info') NOT NULL,
        category      ENUM(
                        'accessibility', 'complexity', 'style',
                        'architecture', 'security', 'spelling', 'duplication'
                      ) NOT NULL,
        file_path     VARCHAR(1024) NOT NULL,
        line_number   INT           NOT NULL,
        col_number    INT           DEFAULT 0,
        message       TEXT          NOT NULL,
        snippet       TEXT          DEFAULT NULL,
        INDEX idx_v4_res_run      (scan_run_id),
        INDEX idx_v4_res_file     (file_path(512)),
        INDEX idx_v4_res_severity (severity),
        INDEX idx_v4_res_category (category),
        INDEX idx_v4_res_tool     (tool_name),
        FOREIGN KEY (scan_run_id) REFERENCES v4_scan_runs(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='V4 unified SARIF findings'
    """,
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_connection(cfg: dict) -> mysql.connector.MySQLConnection:
    """Open a connection from the cfg dict (same structure as db_writer.py)."""
    db = cfg["db"]
    return mysql.connector.connect(
        host       = db.get("host",     "localhost"),
        port       = int(db.get("port", 3306)),
        user       = db["user"],
        password   = db["password"],
        database   = db["database"],      # code_audit_db (shared, no conflict)
        autocommit = False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def setup_schema(cfg: dict) -> None:
    """
    Ensure the two V4 tables exist.

    Uses CREATE TABLE IF NOT EXISTS — safe to call on every run.
    Never drops, truncates, or modifies any existing table.

    Args:
        cfg: Parsed project_config.yaml dict (must have cfg["db"]).
    """
    db = cfg["db"]

    # Connect without specifying database so we can ensure DB exists
    conn = mysql.connector.connect(
        host     = db.get("host",     "localhost"),
        port     = int(db.get("port", 3306)),
        user     = db["user"],
        password = db["password"],
    )
    cur = conn.cursor()

    # Create database if it doesn't exist (same DB as existing pipeline)
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db['database']}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{db['database']}`")

    for ddl in _V4_DDL:
        cur.execute(ddl)
        logger.debug("[v4/db_loader] DDL executed OK.")

    conn.commit()
    conn.close()
    logger.info(
        "[v4/db_loader] V4 schema ready in database '%s' "
        "(tables: v4_scan_runs, v4_sarif_results).",
        db["database"],
    )


def ingest_report(cfg: dict, report: SARIFReport) -> int:
    """
    Persist a complete SARIFReport to MySQL.

    Writes:
      1. One row into v4_scan_runs (header with aggregate stats).
      2. N rows into v4_sarif_results (one per SARIFResult finding).

    Args:
        cfg:    Parsed project_config.yaml dict.
        report: A validated SARIFReport Pydantic object.

    Returns:
        scan_run_id (int) of the newly inserted scan_run row.

    Raises:
        TypeError  : If report is not a SARIFReport instance.
        RuntimeError: On DB write failure (after rollback).
    """
    if not isinstance(report, SARIFReport):
        raise TypeError(
            f"ingest_report() requires a SARIFReport instance, got {type(report).__name__}. "
            "Never pass raw dicts or legacy taskX formats here."
        )

    summary   = report.summary()
    by_sev    = summary["by_severity"]
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_connection(cfg)
    cur  = conn.cursor()

    try:
        # ── 1. Insert scan_run header row ─────────────────────────────────
        cur.execute(
            """
            INSERT INTO v4_scan_runs
                (project, base_path, scanned_at,
                 total_findings, errors_count, warnings_count, info_count,
                 health_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                report.project,
                report.base_path,
                now,
                len(report.results),
                by_sev.get(Severity.ERROR.value,   0),
                by_sev.get(Severity.WARNING.value, 0),
                by_sev.get(Severity.INFO.value,    0),
                report.health_score(),
            ),
        )
        scan_run_id = cur.lastrowid
        logger.info(
            "[v4/db_loader] Created scan_run id=%d for project='%s' "
            "(%d findings, health=%.1f).",
            scan_run_id, report.project, len(report.results), report.health_score(),
        )

        # ── 2. Bulk insert SARIF findings ─────────────────────────────────
        insert_sql = """
            INSERT INTO v4_sarif_results
                (scan_run_id, tool_name, rule_id, severity, category,
                 file_path, line_number, col_number, message, snippet)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        rows = [
            (
                scan_run_id,
                r.tool_name,
                r.rule_id,
                r.severity,    # already str via use_enum_values=True
                r.category,    # already str
                r.file_path,
                r.line,
                r.column,
                r.message,
                r.snippet,
            )
            for r in report.results
        ]

        if rows:
            cur.executemany(insert_sql, rows)
            logger.info(
                "[v4/db_loader] Inserted %d SARIF results into v4_sarif_results.",
                len(rows),
            )

        conn.commit()
        return scan_run_id

    except Exception as exc:
        conn.rollback()
        logger.error("[v4/db_loader] Write failed, rolled back: %s", exc)
        raise RuntimeError(f"V4 DB ingestion failed: {exc}") from exc

    finally:
        cur.close()
        conn.close()


def get_scan_run(cfg: dict, scan_run_id: int) -> dict | None:
    """
    Fetch a single scan_run row by ID.
    Returns a dict or None if not found.
    """
    conn = _get_connection(cfg)
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT * FROM v4_scan_runs WHERE id = %s",
            (scan_run_id,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def get_results_for_run(
    cfg: dict,
    scan_run_id: int,
    *,
    severity: str | None = None,
    category: str | None = None,
    file_path: str | None = None,
) -> list[dict]:
    """
    Query v4_sarif_results for a given scan run with optional filters.

    Args:
        cfg:         Config dict.
        scan_run_id: ID returned by ingest_report().
        severity:    Optional filter — "error" | "warning" | "info"
        category:    Optional filter — any Category enum value
        file_path:   Optional partial file path filter (LIKE match)

    Returns:
        List of result dicts from v4_sarif_results.
    """
    conn = _get_connection(cfg)
    cur  = conn.cursor(dictionary=True)
    try:
        where  = ["scan_run_id = %s"]
        params: list = [scan_run_id]

        if severity:
            where.append("severity = %s")
            params.append(severity)
        if category:
            where.append("category = %s")
            params.append(category)
        if file_path:
            where.append("file_path LIKE %s")
            params.append(f"%{file_path}%")

        sql = f"SELECT * FROM v4_sarif_results WHERE {' AND '.join(where)} ORDER BY id"
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def export_run_to_json(cfg: dict, scan_run_id: int, output_path: str) -> None:
    """
    Export a complete scan run (header + all findings) to a JSON file.
    Mirrors the export_db_to_json() pattern from db_writer.py.

    Args:
        cfg:          Config dict.
        scan_run_id:  ID of the run to export.
        output_path:  Absolute path where the JSON file will be written.
    """
    conn = _get_connection(cfg)
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM v4_scan_runs WHERE id = %s", (scan_run_id,))
        run = cur.fetchone()
        if not run:
            logger.warning("[v4/db_loader] scan_run id=%d not found.", scan_run_id)
            return

        # Serialize datetime fields
        if isinstance(run.get("scanned_at"), datetime):
            run["scanned_at"] = run["scanned_at"].strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            "SELECT * FROM v4_sarif_results WHERE scan_run_id = %s ORDER BY id",
            (scan_run_id,),
        )
        results = cur.fetchall()

        payload = {
            "export_date" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scan_run"    : run,
            "results"     : results,
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        logger.info(
            "[v4/db_loader] Exported scan_run id=%d → %s (%d findings).",
            scan_run_id, output_path, len(results),
        )
    finally:
        cur.close()
        conn.close()
