"""
Module: db_report_loader.py
Description: A read-only database loader for Task 7. It fetches data from the underlying
             MySQL tables ensuring a decoupled logic layer for the Issue Detection Engine.
"""

import os
import logging
import mysql.connector

logger = logging.getLogger(__name__)

def get_db_connection(cfg: dict):
    """
    Opens and returns a MySQL connection using the project configuration.
    Never hardcode host, user, password, or database.
    Supports environment variable overrides.
    """
    db = cfg["db"]
    try:
        return mysql.connector.connect(
            host     = os.getenv("MYSQL_HOST", db.get("host", "localhost")),
            port     = int(os.getenv("MYSQL_PORT", db.get("port", 3306))),
            user     = os.getenv("MYSQL_USER", db.get("user", "root")),
            password = os.getenv("MYSQL_PASSWORD", db.get("password", "")),
            database = os.getenv("MYSQL_DATABASE", db.get("database", "code_audit_db"))
        )
    except mysql.connector.Error as e:
        logger.error("[db_report_loader] Database connection failed: %s", e)
        raise

def _fetch_all(cfg: dict, query: str, params: tuple = ()) -> list:
    """Helper purely for executing read-only SELECT queries returning list of dicts."""
    conn = get_db_connection(cfg)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params)
        return cur.fetchall()
    except Exception as e:
        logger.error("[db_report_loader] Query failed: %s -> %s", query, e)
        return []
    finally:
        cur.close()
        conn.close()

def load_component_complexity(cfg: dict) -> list:
    """
    SELECT * FROM vue_files
    Returns all file metrics.
    """
    return _fetch_all(cfg, "SELECT * FROM vue_files")

def load_api_calls(cfg: dict) -> list:
    """
    SELECT * FROM api_calls
    Returns all MQL calls found.
    """
    return _fetch_all(cfg, "SELECT * FROM api_calls")

def load_file_flags(cfg: dict) -> list:
    """
    SELECT * FROM file_flags
    Returns all flags per file.
    """
    return _fetch_all(cfg, "SELECT * FROM file_flags")

def load_ui_extractions(cfg: dict) -> list:
    """
    SELECT * FROM ui_extractions
    Returns all UI element data.
    """
    return _fetch_all(cfg, "SELECT * FROM ui_extractions")

def load_ui_defects(cfg: dict) -> list:
    """
    SELECT * FROM ui_defects
    Returns all UI consistency defects.
    """
    return _fetch_all(cfg, "SELECT * FROM ui_defects")

def load_accessibility_defects(cfg: dict) -> list:
    """
    SELECT * FROM accessibility_defects
    Returns all accessibility violations.
    """
    return _fetch_all(cfg, "SELECT * FROM accessibility_defects")

def load_all_issues_for_file(cfg: dict, file_path: str) -> dict:
    """
    Joins all tables for one specific file, returning everything known about it
    in a single dictionary using separate queries to construct the object.
    """
    # Grab the baseline record
    files = _fetch_all(cfg, "SELECT * FROM vue_files WHERE file_path = %s", (file_path,))
    if not files:
        return {}
    file_record = files[0]
    file_id = file_record["id"]
    
    return {
        "vue_file": file_record,
        "api_calls": _fetch_all(cfg, "SELECT * FROM api_calls WHERE file_id = %s", (file_id,)),
        "file_flags": _fetch_all(cfg, "SELECT * FROM file_flags WHERE file_id = %s", (file_id,)),
        "ui_extractions": _fetch_all(cfg, "SELECT * FROM ui_extractions WHERE file_id = %s", (file_id,)),
        "ui_defects": _fetch_all(cfg, "SELECT * FROM ui_defects WHERE file_id = %s", (file_id,)),
        "accessibility_defects": _fetch_all(cfg, "SELECT * FROM accessibility_defects WHERE file_id = %s", (file_id,))
    }

def load_high_risk_files(cfg: dict) -> list:
    """
    Query files that have flags containing:
    MONOLITH_COMPONENT, CRITICAL_COMPONENT, VERY_LARGE_COMPONENT, EXCESSIVE_API_USAGE
    Returns list of high risk file paths.
    """
    query = """
        SELECT DISTINCT vf.file_path 
        FROM vue_files vf
        JOIN file_flags ff ON vf.id = ff.file_id
        WHERE ff.flag_name IN (
            'MONOLITH_COMPONENT', 
            'CRITICAL_COMPONENT', 
            'VERY_LARGE_COMPONENT', 
            'EXCESSIVE_API_USAGE'
        )
    """
    results = _fetch_all(cfg, query)
    return [row["file_path"] for row in results]

def search_files(cfg: dict, pattern: str) -> list:
    """
    Search for files matching a partial path or name.
    Useful for helping the agent find the exact file_path.
    """
    query = "SELECT file_path FROM vue_files WHERE file_path LIKE %s LIMIT 10"
    params = (f"%{pattern}%",)
    results = _fetch_all(cfg, query, params)
    return [row["file_path"] for row in results]
