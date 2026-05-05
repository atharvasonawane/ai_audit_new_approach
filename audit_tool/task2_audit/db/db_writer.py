"""
db/db_writer.py
===============
Creates the MySQL schema and writes all scan results for every .vue file.

Tables:
    vue_files    : one row per file — path, metrics, flag_count, timestamp
    api_calls    : every MQL call found (method, line, flags)
    file_flags   : every triggered flag per file
    file_metrics : raw numbers (lines, methods, computed, etc.)
"""

import logging
import json
from datetime import datetime
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
_DDL = [
    """
    CREATE TABLE IF NOT EXISTS vue_files (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        file_path     VARCHAR(1024) NOT NULL,
        module        VARCHAR(255),
        script_lines  INT DEFAULT 0,
        methods       INT DEFAULT 0,
        computed      INT DEFAULT 0,
        watchers      INT DEFAULT 0,
        template_lines INT DEFAULT 0,
        child_components INT DEFAULT 0,
        max_nesting_depth INT DEFAULT 0,
        api_total     INT DEFAULT 0,
        api_mounted   INT DEFAULT 0,
        payload_keys  INT DEFAULT 0,
        payload_depth INT DEFAULT 0,
        payload_size_kb FLOAT DEFAULT 0.0,
        flag_count    INT DEFAULT 0,
        confidence    VARCHAR(10),
        scanned_at    DATETIME,
        UNIQUE KEY uq_file_path (file_path(512))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS api_calls (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        file_id      INT NOT NULL,
        api_type     VARCHAR(20),
        method_name  VARCHAR(255),
        full_match   VARCHAR(300),
        in_mounted   TINYINT(1) DEFAULT 0,
        in_loop      TINYINT(1) DEFAULT 0,
        line_number  INT,
        FOREIGN KEY (file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS file_flags (
        id        INT AUTO_INCREMENT PRIMARY KEY,
        file_id   INT NOT NULL,
        flag_name VARCHAR(100),
        category  VARCHAR(50),
        line_number INT DEFAULT 0,
        FOREIGN KEY (file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS ui_extractions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_id INT NOT NULL,
        element_category VARCHAR(50),
        text_content TEXT,
        css_class VARCHAR(255),
        text_type VARCHAR(50),
        FOREIGN KEY (file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS ui_defects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_id INT NOT NULL,
        defect_type VARCHAR(50),
        severity VARCHAR(20),
        element_type VARCHAR(50),
        trigger_text TEXT,
        expected_text TEXT,
        FOREIGN KEY (file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS accessibility_defects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_id INT NOT NULL,
        file_path VARCHAR(1024),
        module VARCHAR(255),
        rule VARCHAR(100),
        defect_type VARCHAR(100),
        element TEXT,
        severity VARCHAR(20),
        line_number INT,
        confidence VARCHAR(20),
        scanned_at DATETIME,
        FOREIGN KEY (file_id) REFERENCES vue_files(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

# Flag → category mapping
_FLAG_CATEGORY = {
    "HIGH_API_USAGE": "API",
    "VERY_HIGH_API_USAGE": "API",
    "EXCESSIVE_API_USAGE": "API",
    "HEAVY_MOUNTED_API": "API",
    "COMPLEX_PAYLOAD": "PAYLOAD",
    "VERY_COMPLEX_PAYLOAD": "PAYLOAD",
    "DEEP_NESTED_PAYLOAD": "PAYLOAD",
    "LARGE_PAYLOAD": "PAYLOAD",
    "LARGE_COMPONENT": "COMPONENT",
    "MANY_METHODS": "COMPONENT",
    "MANY_COMPUTED": "COMPONENT",
    "MANY_WATCHERS": "COMPONENT",
    "HIGH_RISK_COMPONENT": "COMBINED",
    "CRITICAL_COMPONENT": "COMBINED",
    "HEAVY_COMPONENT": "COMBINED",
    "MONOLITH_COMPONENT": "COMBINED",
    "COMPLEX_HEAVY_COMPONENT": "COMBINED",
    "ARCHITECTURE_CONCERN": "COMBINED",
    "API_IN_LOOP": "PATTERN",
    "API_CHAINING": "PATTERN",
    "DEPENDENT_API_CALLS": "PATTERN",
    "DUPLICATE_API_CALLS": "PATTERN",
    "COMPLEX_TEMPLATE": "TEMPLATE",
    "DEEP_NESTED_TEMPLATE": "TEMPLATE",
    "MANY_CHILDREN": "TEMPLATE",
}


def _get_connection(cfg: dict):
    """Open and return a mysql.connector connection from config dict."""
    import mysql.connector

    db = cfg["db"]
    return mysql.connector.connect(
        host=db.get("host", "localhost"),
        port=int(db.get("port", 3306)),
        user=db["user"],
        password=db["password"],
        database=db["database"],
        autocommit=False,
    )


def setup_schema(cfg: dict) -> None:
    """
    Ensure the MySQL schema exists without dropping data.

    Called once at the start of every scan run to ensure tables exist.
    Will not destroy leftover data from previous runs.

    Args:
        cfg (dict): Parsed project_config.yaml.
    """
    import mysql.connector

    db = cfg["db"]
    conn = mysql.connector.connect(
        host=db.get("host", "localhost"),
        port=int(db.get("port", 3306)),
        user=db["user"],
        password=db["password"],
    )
    cur = conn.cursor()

    # Create DB if missing
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db['database']}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{db['database']}`")

    # Recreate all tables fresh if missing
    for ddl in _DDL:
        cur.execute(ddl)

    # Safe alter table for file_flags
    try:
        cur.execute("ALTER TABLE file_flags ADD COLUMN line_number INT DEFAULT 0")
    except mysql.connector.Error as e:
        # Error 1060: Duplicate column name
        if e.errno != 1060:
            logger.warning("[db_writer] Failed to alter file_flags table: %s", e)

    conn.commit()
    conn.close()
    logger.info(
        "[db_writer] Database '%s' schema initialized/verified.", db["database"]
    )


def write_file_result(cfg: dict, result: dict) -> None:
    """
    Insert (or replace) one .vue file's full analysis result into MySQL.

    Uses INSERT ... ON DUPLICATE KEY UPDATE so re-running the scanner
    updates existing rows instead of duplicating them.

    Args:
        cfg    (dict): Parsed project_config.yaml.
        result (dict): The full result dict built by the orchestrator.
    """
    conn = _get_connection(cfg)
    cur = conn.cursor()

    metrics = result.get("extracted_metrics", {})
    mql_calls = result.get("api_calls", [])
    flags = result.get("flags_triggered", [])
    filepath = result.get("file", "")
    module = result.get("module", "")
    conf = result.get("confidence", "HIGH")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize filepath BEFORE inserting — all downstream consumers
    # (task5, task7, db_report_loader) read from this table, so clean
    # paths here eliminate the need to normalize on every read.
    base_path = cfg.get("base_path", "") if cfg else ""
    if base_path:
        from extractors.path_utils import normalize_path

        filepath = normalize_path(filepath, base_path)

    try:
        # ── 1. vue_files ─────────────────────────────────────────────────
        cur.execute(
            """
            INSERT INTO vue_files
                (file_path, module, script_lines, methods, computed, watchers,
                 template_lines, child_components, max_nesting_depth,
                 api_total, api_mounted, payload_keys, payload_depth, payload_size_kb,
                 flag_count, confidence, scanned_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                module=VALUES(module),
                script_lines=VALUES(script_lines), methods=VALUES(methods),
                computed=VALUES(computed), watchers=VALUES(watchers),
                template_lines=VALUES(template_lines),
                child_components=VALUES(child_components),
                max_nesting_depth=VALUES(max_nesting_depth),
                api_total=VALUES(api_total), api_mounted=VALUES(api_mounted),
                payload_keys=VALUES(payload_keys), payload_depth=VALUES(payload_depth),
                payload_size_kb=VALUES(payload_size_kb),
                flag_count=VALUES(flag_count), confidence=VALUES(confidence),
                scanned_at=VALUES(scanned_at)
        """,
            (
                filepath,
                module,
                metrics.get("script_lines", 0),
                metrics.get("methods", 0),
                metrics.get("computed", 0),
                metrics.get("watchers", 0),
                metrics.get("template_lines", 0),
                metrics.get("child_components", 0),
                metrics.get("max_nest_depth", 0),
                metrics.get("api_total", 0),
                metrics.get("api_in_mounted", 0),
                metrics.get("payload_keys", 0),
                metrics.get("payload_depth", 0),
                metrics.get("payload_size_kb", 0.0),
                len(flags),
                conf,
                now,
            ),
        )
        file_id = cur.lastrowid or _get_file_id(cur, filepath)

        # ── 2. Clear old api_calls and file_flags for this file ───────────
        cur.execute("DELETE FROM api_calls  WHERE file_id = %s", (file_id,))
        cur.execute("DELETE FROM file_flags WHERE file_id = %s", (file_id,))

        # ── 3. api_calls ─────────────────────────────────────────────────
        for call in mql_calls:
            cur.execute(
                """
                INSERT INTO api_calls
                    (file_id, api_type, method_name, full_match, in_mounted, in_loop, line_number)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
                (
                    file_id,
                    call.get("type", "MQL"),
                    call.get("method", ""),
                    call.get("full_match", ""),
                    1 if call.get("in_mounted") else 0,
                    1 if call.get("in_loop") else 0,
                    call.get("line_number", 0),
                ),
            )

        # ── 4. file_flags ─────────────────────────────────────────────────
        for flag_obj in flags:
            if isinstance(flag_obj, dict):
                flag = flag_obj["flag"]
                line = flag_obj.get("line_number")
            else:
                flag = flag_obj
                line = None
            category = _FLAG_CATEGORY.get(flag, "OTHER")
            cur.execute(
                """
                INSERT INTO file_flags (file_id, flag_name, category, line_number)
                VALUES (%s,%s,%s,%s)
            """,
                (file_id, flag, category, line or 0),
            )

        conn.commit()
        logger.debug("[db_writer] Saved: %s (%d flags)", filepath, len(flags))

    except Exception as exc:
        conn.rollback()
        logger.error("[db_writer] Failed to write '%s': %s", filepath, exc)
        raise
    finally:
        conn.close()


def _get_file_id(cur, filepath: str) -> int:
    """Fetch the id of an existing vue_files row by file_path."""
    cur.execute("SELECT id FROM vue_files WHERE file_path = %s", (filepath,))
    row = cur.fetchone()
    return row[0] if row else 0


def export_db_to_json(cfg: dict, output_path: str) -> None:
    """
    Query the complete contents of the 3 database tables and dump them to a JSON file.
    This fulfills the requirement of exporting the entire Task 2 DB natively to JSON.
    """
    conn = _get_connection(cfg)
    cur = conn.cursor(dictionary=True)

    export_data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database": cfg["db"].get("database", "code_audit_db"),
    }

    try:
        # 1. vue_files
        cur.execute("SELECT * FROM vue_files")
        files = cur.fetchall()
        for f in files:
            if isinstance(f.get("scanned_at"), datetime):
                f["scanned_at"] = f["scanned_at"].strftime("%Y-%m-%d %H:%M:%S")
        export_data["vue_files"] = files

        # 2. api_calls
        cur.execute("SELECT * FROM api_calls")
        export_data["api_calls"] = cur.fetchall()

        # 3. file_flags
        cur.execute("SELECT * FROM file_flags")
        export_data["file_flags"] = cur.fetchall()

        # 4. ui_defects
        cur.execute("SELECT * FROM ui_defects")
        export_data["ui_defects"] = cur.fetchall()

        # 5. accessibility_defects
        cur.execute("SELECT * FROM accessibility_defects")
        defects = cur.fetchall()
        for d in defects:
            if isinstance(d.get("scanned_at"), datetime):
                d["scanned_at"] = d["scanned_at"].strftime("%Y-%m-%d %H:%M:%S")
        export_data["accessibility_defects"] = defects

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        logger.info("[db_writer] Database exported to JSON: %s", output_path)

    except Exception as exc:
        logger.error("[db_writer] Failed to export database to JSON: %s", exc)
    finally:
        cur.close()
        conn.close()


def write_ui_defect(cfg: dict, defect: dict) -> None:
    """
    Insert a single ui_defect into the MySQL database.
    """
    conn = _get_connection(cfg)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO ui_defects
                (file_id, defect_type, severity, element_type, trigger_text, expected_text)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (
                defect.get("file_id", 0),
                defect.get("defect_type", ""),
                defect.get("severity", ""),
                defect.get("element_type", ""),
                defect.get("trigger_text", ""),
                defect.get("expected_text", ""),
            ),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("[db_writer] Failed to write ui_defect: %s", exc)
    finally:
        cur.close()
        conn.close()


def write_accessibility_defect(cfg: dict, defect: dict) -> None:
    """
    Insert a single accessibility_defect into the MySQL database.
    """
    conn = _get_connection(cfg)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO accessibility_defects
                (file_id, file_path, module, rule, defect_type, element, severity, line_number, confidence, scanned_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                defect.get("file_id", 0),
                defect.get("file_path", ""),
                defect.get("module", ""),
                defect.get("rule", ""),
                defect.get("defect_type", ""),
                defect.get("element", ""),
                defect.get("severity", ""),
                defect.get("line_number", 0),
                defect.get("confidence", "HIGH"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("[db_writer] Failed to write accessibility_defect: %s", exc)
    finally:
        cur.close()
        conn.close()


def write_eslint_flags(cfg: dict, eslint_results: list) -> dict:
    """
    Insert ESLint findings into the appropriate MySQL tables based on rule type.
    
    Rules starting with 'vuejs-accessibility/' are written to accessibility_defects.
    All other rules (including 'vue/') are written to file_flags.
    
    Args:
        cfg: Parsed project_config.yaml
        eslint_results: List of dicts from parse_eslint_results()
        
    Returns:
        Dict with counts: {'file_flags': int, 'accessibility_defects': int}
    """
    if not eslint_results:
        return {"file_flags": 0, "accessibility_defects": 0}
        
    conn = _get_connection(cfg)
    cur = conn.cursor()
    file_flags_written = 0
    accessibility_written = 0
    
    # Import path normalizer
    base_path = cfg.get("base_path", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        for issue in eslint_results:
            file_path = issue.get("file_path", "")
            rule_id = issue.get("rule_id", "")
            
            # Normalize path to match vue_files table format
            if base_path:
                from extractors.path_utils import normalize_path
                normalized_path = normalize_path(file_path, base_path)
            else:
                normalized_path = file_path.replace("\\", "/")
            
            # Look up file_id from vue_files
            file_id = _get_file_id(cur, normalized_path)
            
            if not file_id:
                logger.warning("[db_writer] Could not find file_id for '%s' — skipping ESLint finding", normalized_path)
                continue
            
            # Determine severity string from ESLint numeric severity (1=warning, 2=error)
            severity_num = issue.get("severity", 0)
            severity_str = "error" if severity_num >= 2 else "warning"
            
            if rule_id.startswith("vuejs-accessibility/"):
                # Write to accessibility_defects
                cur.execute(
                    """
                    INSERT INTO accessibility_defects
                        (file_id, file_path, module, rule, defect_type, element, severity, line_number, confidence, scanned_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        file_id,
                        normalized_path,
                        cfg.get("module", ""),
                        rule_id,
                        "ESLint Accessibility",
                        issue.get("message", ""),
                        severity_str,
                        issue.get("line", 0),
                        "HIGH",
                        now,
                    ),
                )
                accessibility_written += 1
            else:
                # Write to file_flags
                cur.execute(
                    """
                    INSERT INTO file_flags (file_id, flag_name, category, line_number)
                    VALUES (%s, %s, %s, %s)
                """,
                    (file_id, rule_id, "ESLINT", issue.get("line", 0)),
                )
                file_flags_written += 1
            
        conn.commit()
        logger.info("[db_writer] Wrote %d ESLint flags to file_flags, %d to accessibility_defects",
                      file_flags_written, accessibility_written)
        
    except Exception as exc:
        conn.rollback()
        logger.error("[db_writer] Failed to write ESLint flags: %s", exc)
    finally:
        cur.close()
        conn.close()
        
    return {"file_flags": file_flags_written, "accessibility_defects": accessibility_written}
