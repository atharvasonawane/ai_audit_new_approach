"""
Flask API Server for Code Audit Librarian
Stage 6 — Read-only JSON API serving SQLite data to Vue.js frontend

All endpoints return JSON with CORS headers.
Dynamic code snippets generated for api_calls, file_flags, and accessibility_defects.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "audit_tool" / "config" / "project_config.yaml"


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


CONFIG = _load_config()
db_config_path = CONFIG.get("db", {}).get("path")
if db_config_path:
    DB_PATH = Path(db_config_path)
    if not DB_PATH.is_absolute():
        DB_PATH = PROJECT_ROOT / DB_PATH
else:
    DB_PATH = PROJECT_ROOT / "audit_history.db"
PROJECT_NAME = CONFIG.get("project_name", "default")
BASE_PATH = CONFIG.get("base_path", "")


# WCAG metadata dictionary for accessibility rules
WCAG_METADATA = {
    "vue/no-static-inline-styles": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Inline styles can interfere with user stylesheets and assistive technologies.",
    },
    "vuejs-accessibility/alt-text": {
        "criterion": "1.1.1 Non-text Content",
        "level": "A",
        "explanation": "Images must have alternative text for screen readers.",
    },
    "vuejs-accessibility/anchor-has-content": {
        "criterion": "2.4.4 Link Purpose",
        "level": "A",
        "explanation": "Links must have discernible text content.",
    },
    "vuejs-accessibility/aria-props": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA attributes must be valid and properly used.",
    },
    "vuejs-accessibility/aria-role": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA roles must be valid HTML5 roles.",
    },
    "vuejs-accessibility/aria-unsupported-elements": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA should not be used on elements that don't support it.",
    },
    "vuejs-accessibility/click-events-have-key-events": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Interactive elements must be keyboard accessible.",
    },
    "vuejs-accessibility/form-control-has-label": {
        "criterion": "3.3.2 Labels or Instructions",
        "level": "A",
        "explanation": "Form controls must have associated labels.",
    },
    "vuejs-accessibility/heading-has-content": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Heading elements must have content for proper document structure.",
    },
    "vuejs-accessibility/iframe-has-title": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "iframes must have a title attribute for context.",
    },
    "vuejs-accessibility/interactive-supports-focus": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Interactive elements must be focusable.",
    },
    "vuejs-accessibility/label-has-for": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Labels must be properly associated with form controls.",
    },
    "vuejs-accessibility/media-has-caption": {
        "criterion": "1.2.2 Captions (Prerecorded)",
        "level": "A",
        "explanation": "Audio and video content must have captions.",
    },
    "vuejs-accessibility/mouse-events-have-key-events": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Mouse event handlers must have keyboard equivalents.",
    },
    "vuejs-accessibility/no-access-key": {
        "criterion": "2.4.1 Bypass Blocks",
        "level": "A",
        "explanation": "Access keys can conflict with assistive technology shortcuts.",
    },
    "vuejs-accessibility/no-autofocus": {
        "criterion": "2.4.3 Focus Order",
        "level": "A",
        "explanation": "Autofocus can disorient users relying on screen readers.",
    },
    "vuejs-accessibility/no-distracting-elements": {
        "criterion": "2.2.2 Pause, Stop, Hide",
        "level": "A",
        "explanation": "Blinking or scrolling content must be controllable.",
    },
    "vuejs-accessibility/no-onchange": {
        "criterion": "3.2.2 On Input",
        "level": "A",
        "explanation": "Form controls should not trigger context changes on input alone.",
    },
    "vuejs-accessibility/no-redundant-roles": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "Don't use ARIA roles that match the element's implicit role.",
    },
    "vuejs-accessibility/role-has-required-aria-props": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA roles must include all required attributes.",
    },
    "vuejs-accessibility/tabindex-no-positive": {
        "criterion": "2.4.3 Focus Order",
        "level": "A",
        "explanation": "Positive tabindex values disrupt natural tab order.",
    },
}


def _db_connect() -> sqlite3.Connection:
    """Create a read-only database connection with Row factory."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to dictionary."""
    return dict(row) if row else {}


def _extract_snippet(file_path: str, line_number: int) -> str:
    """
    Extract a 5-line code snippet (2 lines above, target line, 2 lines below).
    Target line is marked with ► prefix.
    """
    try:
        # Try absolute path first
        path = Path(file_path)
        if not path.exists() and BASE_PATH:
            # Try relative to base_path
            path = Path(BASE_PATH) / file_path
        
        if not path.exists():
            return f"[File not found: {file_path}]"
        
        lines = path.read_text(encoding="utf-8").splitlines()
        
        if line_number < 1 or line_number > len(lines):
            return f"[Line {line_number} out of range]"
        
        start = max(1, line_number - 2)
        end = min(len(lines), line_number + 2)
        
        snippet_lines = []
        for idx in range(start, end + 1):
            prefix = "► " if idx == line_number else "  "
            snippet_lines.append(f"{prefix}{idx}: {lines[idx - 1]}")
        
        return "\n".join(snippet_lines)
    
    except Exception as e:
        return f"[Error reading file: {e}]"


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """
    GET /api/summary
    Returns aggregate project statistics.
    """
    try:
        conn = _db_connect()
        
        # Total files
        total_files = conn.execute(
            "SELECT COUNT(*) as count FROM vue_files WHERE project_name = ?",
            (PROJECT_NAME,)
        ).fetchone()["count"]
        
        # Total ESLint flags
        total_eslint = conn.execute(
            "SELECT COALESCE(SUM(eslint_flag_count), 0) as count FROM vue_files WHERE project_name = ?",
            (PROJECT_NAME,)
        ).fetchone()["count"]
        
        # AI issues by severity
        ai_issues = conn.execute(
            """
            SELECT severity, COUNT(*) as count
            FROM ai_issues
            WHERE project_name = ? AND phase = 'file_analysis'
            GROUP BY severity
            """,
            (PROJECT_NAME,)
        ).fetchall()
        
        issues_by_severity = {"High": 0, "Medium": 0, "Low": 0}
        for row in ai_issues:
            severity = row["severity"] or "Low"
            if severity in issues_by_severity:
                issues_by_severity[severity] = row["count"]
        
        # Average complexity
        avg_complexity = conn.execute(
            """
            SELECT AVG(COALESCE(cyclomatic_complexity, 0)) as avg_complexity
            FROM vue_files
            WHERE project_name = ?
            """,
            (PROJECT_NAME,)
        ).fetchone()["avg_complexity"] or 0
        
        # Total accessibility defects
        total_accessibility = conn.execute(
            "SELECT COUNT(*) as count FROM accessibility_defects WHERE project_name = ?",
            (PROJECT_NAME,)
        ).fetchone()["count"]
        
        conn.close()
        
        return jsonify({
            "project_name": PROJECT_NAME,
            "total_files": total_files,
            "total_eslint_flags": total_eslint,
            "total_accessibility_defects": total_accessibility,
            "ai_issues_by_severity": issues_by_severity,
            "ai_issues_total": sum(issues_by_severity.values()),
            "average_complexity": round(avg_complexity, 2)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/worst-offenders", methods=["GET"])
def get_worst_offenders():
    """
    GET /api/worst-offenders?limit=10
    Returns top N files by composite score.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT
                vf.file_path,
                vf.script_lines,
                vf.methods,
                vf.api_total,
                vf.api_in_loop,
                vf.max_nesting_depth,
                vf.cyclomatic_complexity,
                COALESCE(vf.eslint_flag_count, 0) as eslint_flag_count,
                COALESCE(ai.cnt, 0) as ai_issue_count,
                (COALESCE(vf.eslint_flag_count, 0) + 
                 COALESCE(ai.cnt, 0) + 
                 COALESCE(vf.api_in_loop, 0) * 2 +
                 COALESCE(vf.max_nesting_depth, 0)) as composite_score
            FROM vue_files vf
            LEFT JOIN (
                SELECT file_path, COUNT(*) as cnt
                FROM ai_issues
                WHERE project_name = ? AND phase = 'file_analysis'
                GROUP BY file_path
            ) ai ON ai.file_path = vf.file_path
            WHERE vf.project_name = ?
            ORDER BY composite_score DESC
            LIMIT ?
            """,
            (PROJECT_NAME, PROJECT_NAME, limit)
        ).fetchall()
        
        conn.close()
        
        offenders = [_row_to_dict(row) for row in rows]
        return jsonify(offenders)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files", methods=["GET"])
def get_files():
    """
    GET /api/files
    Returns list of all scanned files with issue counts.
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT
                vf.file_path,
                vf.script_lines,
                vf.template_lines,
                COALESCE(vf.eslint_flag_count, 0) as eslint_flag_count,
                COALESCE(acc.cnt, 0) as accessibility_count,
                COALESCE(ai.cnt, 0) as ai_issue_count,
                COALESCE(ai.high_cnt, 0) as high_severity_count,
                COALESCE(ai.medium_cnt, 0) as medium_severity_count,
                COALESCE(ai.low_cnt, 0) as low_severity_count
            FROM vue_files vf
            LEFT JOIN (
                SELECT file_path, COUNT(*) as cnt
                FROM accessibility_defects
                WHERE project_name = ?
                GROUP BY file_path
            ) acc ON acc.file_path = vf.file_path
            LEFT JOIN (
                SELECT 
                    file_path,
                    COUNT(*) as cnt,
                    SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as high_cnt,
                    SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) as medium_cnt,
                    SUM(CASE WHEN severity = 'Low' THEN 1 ELSE 0 END) as low_cnt
                FROM ai_issues
                WHERE project_name = ? AND phase = 'file_analysis'
                GROUP BY file_path
            ) ai ON ai.file_path = vf.file_path
            WHERE vf.project_name = ?
            ORDER BY vf.file_path
            """,
            (PROJECT_NAME, PROJECT_NAME, PROJECT_NAME)
        ).fetchall()
        
        conn.close()
        
        files = [_row_to_dict(row) for row in rows]
        return jsonify(files)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-metrics/<path:file_path>", methods=["GET"])
def get_file_metrics(file_path: str):
    """
    GET /api/file-metrics/<path:file_path>
    Returns full metrics row for a file.
    """
    try:
        conn = _db_connect()
        row = conn.execute(
            """
            SELECT * FROM vue_files
            WHERE project_name = ? AND file_path = ?
            """,
            (PROJECT_NAME, file_path)
        ).fetchone()
        
        conn.close()
        
        if not row:
            return jsonify({"error": "File not found"}), 404
        
        return jsonify(_row_to_dict(row))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-api-calls/<path:file_path>", methods=["GET"])
def get_file_api_calls(file_path: str):
    """
    GET /api/file-api-calls/<path:file_path>
    Returns all API calls for a file with dynamically generated code snippets.
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT * FROM api_calls
            WHERE project_name = ? AND file_path = ?
            ORDER BY line_number
            """,
            (PROJECT_NAME, file_path)
        ).fetchall()
        
        conn.close()
        
        api_calls = []
        for row in rows:
            call = _row_to_dict(row)
            # Generate code snippet dynamically
            call["code_snippet"] = _extract_snippet(file_path, call.get("line_number", 0))
            api_calls.append(call)
        
        return jsonify(api_calls)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-accessibility/<path:file_path>", methods=["GET"])
def get_file_accessibility(file_path: str):
    """
    GET /api/file-accessibility/<path:file_path>
    Returns accessibility defects with WCAG metadata and code snippets.
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT * FROM accessibility_defects
            WHERE project_name = ? AND file_path = ?
            ORDER BY line_number
            """,
            (PROJECT_NAME, file_path)
        ).fetchall()
        
        conn.close()
        
        defects = []
        for row in rows:
            defect = _row_to_dict(row)
            rule = defect.get("rule", "")
            
            # Add WCAG metadata from dictionary
            metadata = WCAG_METADATA.get(rule, {
                "criterion": "Unknown",
                "level": "A",
                "explanation": "No metadata available for this rule."
            })
            
            defect["wcag_criterion"] = metadata["criterion"]
            defect["wcag_level"] = metadata["level"]
            defect["wcag_explanation"] = metadata["explanation"]
            
            # Generate code snippet dynamically
            defect["code_snippet"] = _extract_snippet(file_path, defect.get("line_number", 0))
            
            defects.append(defect)
        
        return jsonify(defects)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-eslint/<path:file_path>", methods=["GET"])
def get_file_eslint(file_path: str):
    """
    GET /api/file-eslint/<path:file_path>
    Returns ESLint flags (non-accessibility) with code snippets.
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT * FROM file_flags
            WHERE project_name = ? AND file_path = ? AND category = 'eslint'
            ORDER BY severity DESC, line_number
            """,
            (PROJECT_NAME, file_path)
        ).fetchall()
        
        conn.close()
        
        flags = []
        for row in rows:
            flag = _row_to_dict(row)
            # Generate code snippet dynamically
            flag["code_snippet"] = _extract_snippet(file_path, flag.get("line_number", 0))
            flags.append(flag)
        
        return jsonify(flags)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-ai-issues/<path:file_path>", methods=["GET"])
def get_file_ai_issues(file_path: str):
    """
    GET /api/file-ai-issues/<path:file_path>
    Returns LLM-generated issues (code snippets already in database).
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT * FROM ai_issues
            WHERE project_name = ? AND file_path = ? AND phase = 'file_analysis'
            ORDER BY 
                CASE severity
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END,
                line_number
            """,
            (PROJECT_NAME, file_path)
        ).fetchall()
        
        conn.close()
        
        issues = [_row_to_dict(row) for row in rows]
        return jsonify(issues)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/executive-summary", methods=["GET"])
def get_executive_summary():
    """
    GET /api/executive-summary
    Returns the synthesis text from the most recent completed audit run.
    """
    try:
        conn = _db_connect()
        row = conn.execute(
            """
            SELECT synthesis_text, completed_at
            FROM audit_runs
            WHERE project_name = ? AND status = 'completed'
            ORDER BY id DESC
            LIMIT 1
            """,
            (PROJECT_NAME,)
        ).fetchone()
        
        conn.close()
        
        if not row or not row["synthesis_text"]:
            return jsonify({
                "synthesis_text": "No executive summary available. Run the full audit pipeline first.",
                "completed_at": None
            })
        
        return jsonify(_row_to_dict(row))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/run-status", methods=["GET"])
def get_run_status():
    """
    GET /api/run-status
    Returns status of the most recent audit run.
    """
    try:
        conn = _db_connect()
        row = conn.execute(
            """
            SELECT id, project_name, started_at, status, last_completed_file, completed_at
            FROM audit_runs
            WHERE project_name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (PROJECT_NAME,)
        ).fetchone()
        
        conn.close()
        
        if not row:
            return jsonify({
                "status": "no_runs",
                "message": "No audit runs found for this project."
            })
        
        return jsonify(_row_to_dict(row))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dependency-graph", methods=["GET"])
def get_dependency_graph():
    """
    GET /api/dependency-graph
    Returns the full graph.json content.
    """
    try:
        # Assuming the graph.json is written to report/frontend/public/graph.json
        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify({"error": "graph.json not found"}), 404
            
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dependency-summary", methods=["GET"])
def get_dependency_summary():
    """
    GET /api/dependency-summary
    Returns only the summary block from graph.json.
    """
    try:
        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify({"error": "graph.json not found"}), 404
            
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data.get("summary", {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_transitive_dependents(file_path: str) -> list:
    """Helper to compute transitive dependents dynamically via BFS on component_relationships"""
    conn = _db_connect()
    rows = conn.execute("SELECT parent_file, child_file FROM component_relationships WHERE project_name = ?", (PROJECT_NAME,)).fetchall()
    conn.close()
    
    # build reverse adjacency list (child -> list of parents)
    adj = {}
    for r in rows:
        p, c = r["parent_file"], r["child_file"]
        if c not in adj:
            adj[c] = []
        adj[c].append(p)
        
    visited = set()
    queue = [file_path]
    while queue:
        curr = queue.pop(0)
        for p in adj.get(curr, []):
            if p not in visited:
                visited.add(p)
                queue.append(p)
    return list(visited)


@app.route("/api/file-dependencies/<path:file_path>", methods=["GET"])
def get_file_dependencies(file_path: str):
    """
    GET /api/file-dependencies/<path:file_path>
    Returns dependency metrics for one specific file, including transitive impact.
    """
    try:
        conn = _db_connect()
        row = conn.execute(
            """
            SELECT * FROM dependency_metrics
            WHERE project_name = ? AND file_path = ?
            """,
            (PROJECT_NAME, file_path)
        ).fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "File not found in dependency metrics"}), 404
            
        data = _row_to_dict(row)
        
        # Format exactly as requested
        result = {
            "file_path": data["file_path"],
            "category": data["node_category"],
            "in_degree": data["in_degree"],
            "out_degree": data["out_degree"],
            "impact_score": data["impact_score"],
            "is_in_cycle": bool(data["is_in_cycle"]),
            "dependencies": json.loads(data["dependencies"] or "[]"),
            "dependents": json.loads(data["dependents"] or "[]"),
            "transitive_impact": get_transitive_dependents(data["file_path"]),
            "cycle": json.loads(data["cycle_members"] or "[]") if data["is_in_cycle"] else None
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orphans", methods=["GET"])
def get_orphans():
    """
    GET /api/orphans
    Returns list of all orphan nodes with their metadata.
    """
    try:
        conn = _db_connect()
        rows = conn.execute(
            """
            SELECT file_path, in_degree, out_degree, impact_score, node_category 
            FROM dependency_metrics 
            WHERE project_name = ? AND node_category = 'orphan'
            """,
            (PROJECT_NAME,)
        ).fetchall()
        conn.close()
        
        orphans = [_row_to_dict(r) for r in rows]
        return jsonify(orphans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cycles", methods=["GET"])
def get_cycles():
    """
    GET /api/cycles
    Returns all detected cycles from graph.json.
    """
    try:
        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify([])
            
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data.get("cycles", []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "project_name": PROJECT_NAME,
        "database": str(DB_PATH),
        "database_exists": DB_PATH.exists()
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Audit Librarian API Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the API server on")
    args = parser.parse_args()

    print("=" * 60)
    print("Code Audit Librarian — Flask API Server (Stage 6)")
    print("=" * 60)
    print(f"Project: {PROJECT_NAME}")
    print(f"Database: {DB_PATH}")
    print(f"Base Path: {BASE_PATH}")
    print("=" * 60)
    print(f"Starting server on http://localhost:{args.port}")
    print(f"API endpoints available at http://localhost:{args.port}/api/*")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=args.port, debug=False)
