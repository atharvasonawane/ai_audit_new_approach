import os
import sqlite3
from flask import Flask, jsonify, abort
from flask_cors import CORS

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "audit_history.db")
)


def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


@app.route("/api/summary", methods=["GET"])
def get_summary():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get latest run status and synthesis
        cursor.execute(
            "SELECT status, synthesis_text FROM audit_runs ORDER BY id DESC LIMIT 1"
        )
        run_row = cursor.fetchone()

        # Calculate severity counts from ai_issues
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) as medium_count,
                SUM(CASE WHEN severity = 'Low' THEN 1 ELSE 0 END) as low_count
            FROM ai_issues
        """)
        issues_row = cursor.fetchone()

        conn.close()

        return jsonify(
            {
                "status": run_row["status"] if run_row else "unknown",
                "synthesis_text": run_row["synthesis_text"] if run_row else None,
                "issues": {
                    "High": issues_row["high_count"] or 0,
                    "Medium": issues_row["medium_count"] or 0,
                    "Low": issues_row["low_count"] or 0,
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to fetch summary: {e}")
        return abort(500)


@app.route("/api/worst-offenders", methods=["GET"])
def get_worst_offenders():
    try:
        conn = get_db_connection()

        query = """
        SELECT 
            v.file_path,
            COALESCE(i.high_count, 0) as high_count,
            COALESCE(i.medium_count, 0) as medium_count,
            COALESCE(i.low_count, 0) as low_count,
            COALESCE(a.api_loop_count, 0) as api_in_loop,
            COALESCE(f.flag_count, 0) as eslint_flag_count,
            (COALESCE(i.high_count, 0) * 3.0 + 
             COALESCE(i.medium_count, 0) * 2.0 + 
             COALESCE(i.low_count, 0) * 1.0 + 
             COALESCE(a.api_loop_count, 0) * 2.0 + 
             COALESCE(f.flag_count, 0) * 0.5) as score
        FROM vue_files v
        LEFT JOIN (
            SELECT file_path, 
                   SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as high_count,
                   SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) as medium_count,
                   SUM(CASE WHEN severity = 'Low' THEN 1 ELSE 0 END) as low_count
            FROM ai_issues 
            GROUP BY file_path
        ) i ON v.file_path = i.file_path
        LEFT JOIN (
            SELECT vue_file_id, COUNT(*) as api_loop_count
            FROM api_calls
            WHERE in_loop = 1
            GROUP BY vue_file_id
        ) a ON v.id = a.vue_file_id
        LEFT JOIN (
            SELECT vue_file_id, COUNT(*) as flag_count
            FROM file_flags
            GROUP BY vue_file_id
        ) f ON v.id = f.vue_file_id
        ORDER BY score DESC
        LIMIT 10
        """

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return jsonify([dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Failed to fetch worst offenders: {e}")
        return abort(500)


@app.route("/api/files", methods=["GET"])
def get_files():
    try:
        conn = get_db_connection()

        query = """
        SELECT 
            v.*,
            COALESCE(i.high_count, 0) as high_issues,
            COALESCE(i.medium_count, 0) as medium_issues,
            COALESCE(i.low_count, 0) as low_issues
        FROM vue_files v
        LEFT JOIN (
            SELECT file_path, 
                   SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as high_count,
                   SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) as medium_count,
                   SUM(CASE WHEN severity = 'Low' THEN 1 ELSE 0 END) as low_count
            FROM ai_issues 
            GROUP BY file_path
        ) i ON v.file_path = i.file_path
        """

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return jsonify([dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Failed to fetch files: {e}")
        return abort(500)


@app.route("/api/file/<path:file_path>", methods=["GET"])
def get_file_detail(file_path):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vue_files WHERE file_path = ?", (file_path,))
        file_row = cursor.fetchone()

        if not file_row:
            conn.close()
            return abort(404, description="File not found")

        file_id = file_row["id"]
        file_data = dict(file_row)

        cursor.execute("SELECT * FROM file_flags WHERE vue_file_id = ?", (file_id,))
        flags = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM ai_issues WHERE file_path = ?", (file_path,))
        issues = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({"metrics": file_data, "flags": flags, "issues": issues})
    except Exception as e:
        logger.error(f"Failed to fetch file detail for {file_path}: {e}")
        return abort(500)


@app.route("/api/dependencies", methods=["GET"])
def get_dependencies():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ai_issues WHERE phase = 'dependency'")
        rows = cursor.fetchall()
        conn.close()

        return jsonify([dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Failed to fetch dependencies: {e}")
        return abort(500)


@app.route("/api/run-status", methods=["GET"])
def get_run_status():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT status, current_phase FROM audit_runs ORDER BY id DESC LIMIT 1"
        )
        run_row = cursor.fetchone()

        # Added simple counts of progress to meet requirement
        cursor.execute("SELECT COUNT(*) as scanned_files FROM vue_files")
        files_scanned = cursor.fetchone()["scanned_files"]

        cursor.execute("SELECT COUNT(*) as issues_found FROM ai_issues")
        issues_found = cursor.fetchone()["issues_found"]

        conn.close()

        if run_row:
            return jsonify(
                {
                    "status": run_row["status"],
                    "current_phase": run_row["current_phase"],
                    "scanned_files": files_scanned,
                    "issues_found": issues_found,
                }
            )
        else:
            return jsonify({"status": "no_run_found"})
    except Exception as e:
        logger.error(f"Failed to fetch run status: {e}")
        return abort(500)


if __name__ == "__main__":
    logger.info("Starting Code Audit Librarian API on port 5000...")
    app.run(debug=True, port=5000)
