"""
ai_pipeline/ai_reporter.py
--------------------------
Stage 6: AI Architectural Issue Reporter
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_tool.utils.logger import get_logger, log_error, log_success
from ai_pipeline.test_llm_connection import load_env_manual, clean_json_response

logger = get_logger(__name__)

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _get_config(root: Path) -> dict:
    config_path = root / "audit_tool" / "project_config.yaml"
    if not config_path.exists():
        log_error(logger, str(config_path), "project_config.yaml not found.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _get_project_name(config: dict) -> str:
    return config.get("project", {}).get("name", "unknown_project")

def _get_ai_config(config: dict) -> tuple[int, int]:
    ai_cfg = config.get("ai", {})
    complex_file_threshold_lines = int(ai_cfg.get("complex_file_threshold_lines", 150))
    batch_size_simple_files = int(ai_cfg.get("batch_size_simple_files", 8))
    return complex_file_threshold_lines, batch_size_simple_files

def _chat_completions_url(base_url: str) -> str:
    u = (base_url or "").strip().rstrip("/")
    if u.endswith("/chat/completions"):
        return u
    return u + "/chat/completions"

def _call_llm(url: str, api_key: str, payload: dict) -> str:
    payload_bytes = json.dumps(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "CodeAuditLibrarian/1.0"
    }
    req = urllib.request.Request(
        url=url,
        data=payload_bytes,
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            response_dict = json.loads(raw)
            return (response_dict["choices"][0]["message"]["content"] or "").strip()
    except urllib.error.HTTPError as exc:
        body_err = ""
        try:
            body_err = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body_err = "<no body>"
        log_error(logger, url, f"HTTPError {exc.code}: {body_err}")
        return ""
    except Exception as exc:
        log_error(logger, url, f"Request failed: {exc}")
        return ""

def _load_file_source(root: Path, file_path: str) -> str:
    abs_path = (root / Path(file_path)).resolve()
    try:
        return abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        log_error(logger, file_path, f"Failed to read source from disk: {exc}")
        return ""

def _file_bundle(conn: sqlite3.Connection, root: Path, file_row: sqlite3.Row) -> dict:
    file_path = str(file_row["file_path"])
    source_code = _load_file_source(root, file_path)

    metrics = {
        "script_lines": int(file_row["script_lines"] or 0),
        "template_lines": int(file_row["template_lines"] or 0),
        "style_lines": int(file_row["style_lines"] or 0),
        "methods": int(file_row["methods"] or 0),
        "computed": int(file_row["computed"] or 0),
        "watchers": int(file_row["watchers"] or 0),
        "props": int(file_row["props"] or 0),
        "emits": int(file_row["emits"] or 0),
        "api_total": int(file_row["api_total"] or 0),
        "api_in_mounted": int(file_row["api_in_mounted"] or 0),
        "api_in_loop": int(file_row["api_in_loop"] or 0),
        "max_nesting_depth": int(file_row["max_nesting_depth"] or 0),
        "cyclomatic_complexity": int(file_row["cyclomatic_complexity"] or 0),
        "payload_size_kb": float(file_row["payload_size_kb"] or 0.0),
    }

    flags_cursor = conn.execute(
        """
        SELECT rule, line_number AS line, severity
        FROM file_flags
        WHERE project_name = ? AND file_path = ?
        ORDER BY line_number ASC
        """,
        (file_row["project_name"], file_path),
    )
    eslint_flags = [
        {"rule": r["rule"], "line": int(r["line"] or 0), "severity": r["severity"]}
        for r in flags_cursor.fetchall()
        if r["rule"]
    ]

    api_cursor = conn.execute(
        """
        SELECT api_type, method_name, line_number, in_mounted, in_loop
        FROM api_calls
        WHERE project_name = ? AND file_path = ?
        ORDER BY line_number ASC
        """,
        (file_row["project_name"], file_path),
    )
    api_calls = [
        {
            "type": r["api_type"],
            "method": r["method_name"],
            "line": int(r["line_number"] or 0),
            "in_mounted": bool(r["in_mounted"]),
            "in_loop": bool(r["in_loop"]),
        }
        for r in api_cursor.fetchall()
    ]

    return {
        "file_path": file_path,
        "source_code": source_code,
        "metrics": metrics,
        "eslint_flags": eslint_flags,
        "api_calls": api_calls,
    }

def _get_processed_files(conn: sqlite3.Connection, project_name: str) -> set[str]:
    cursor = conn.execute(
        "SELECT DISTINCT file_path FROM ai_issues WHERE project_name = ? AND phase = 'per_file'",
        (project_name,)
    )
    return {r["file_path"] for r in cursor.fetchall()}

def _insert_ai_issues(conn: sqlite3.Connection, project_name: str, file_path: str, issues: list[dict]) -> None:
    for issue in issues:
        if not isinstance(issue, dict):
            logger.warning("Skipping invalid issue format for %s: %s", file_path, issue)
            continue
            
        raw_sev = issue.get("severity", "Medium")
        severity = str(raw_sev).capitalize() if raw_sev else "Medium"
        if severity not in ("High", "Medium", "Low"):
            severity = "Medium"
            
        conn.execute(
            """
            INSERT INTO ai_issues 
            (project_name, file_path, phase, issue_category, description, severity, line_number, code_snippet, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_name,
                file_path,
                'per_file',
                issue.get("issue_category"),
                issue.get("description"),
                severity,
                int(issue.get("line_number", 0)),
                issue.get("code_snippet"),
                issue.get("recommendation")
            )
        )
    conn.commit()

def run_reporter() -> None:
    logger.info("[AI Phase 2/3] Starting per-file architectural analysis...")
    
    root = _repo_root()
    load_env_manual(str(root / ".env"))
    
    base_url = os.getenv("OPENWEBUI_BASE_URL") or os.getenv("LLM_BASE_URL")
    api_key = os.getenv("OPENWEBUI_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    
    if not base_url or not api_key or not model:
        log_error(logger, ".env", "Missing Base URL / API Key / Model in .env.")
        return

    config = _get_config(root)
    project_name = _get_project_name(config)
    complex_threshold, batch_size = _get_ai_config(config)

    db_path = root / "audit_tool" / "audit_history.db"
    if not db_path.exists():
        log_error(logger, str(db_path), "audit_history.db not found.")
        return
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.execute("SELECT * FROM vue_files WHERE project_name = ?", (project_name,))
        all_files = cursor.fetchall()
        
        if not all_files:
            logger.warning("No files found in database for project %s.", project_name)
            return

        complex_files = [f for f in all_files if int(f["script_lines"] or 0) >= complex_threshold]
        simple_files = [f for f in all_files if int(f["script_lines"] or 0) < complex_threshold]

        processed_files = _get_processed_files(conn, project_name)

        url = _chat_completions_url(base_url)

        # ── Process Complex Files ──────────────────────────────────────────────────────────
        for file_row in complex_files:
            file_path = file_row["file_path"]
            if file_path in processed_files:
                logger.info("[SKIPPED] %s already processed.", file_path)
                continue

            bundle = _file_bundle(conn, root, file_row)
            
            system_prompt = """You are a Senior Frontend Architect reviewing a single Vue.js component. You have the full source code plus AST metrics and ESLint findings. Focus ONLY on architectural issues (State Management Bloat, Prop Drilling, Component Over-responsibility, API Flow Issues, Logic Misplacement, Performance Risks). For every issue provide: exact line number, 3-5 line code snippet, concrete actionable recommendation. Return a JSON array only. No preamble. No markdown code fences. Schema: [{'issue_category': '...', 'description': '...', 'severity': 'High|Medium|Low', 'line_number': 0, 'code_snippet': '...', 'recommendation': '...'}] If no issues, return []"""
            
            user_prompt = f"File: {file_path}\n{json.dumps(bundle, ensure_ascii=False)}"

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            
            raw_response = _call_llm(url, api_key, payload)
            if not raw_response:
                continue

            cleaned_response = clean_json_response(raw_response)
            
            try:
                issues = json.loads(cleaned_response)
            except json.JSONDecodeError:
                payload["messages"].append({"role": "assistant", "content": raw_response})
                payload["messages"].append({"role": "user", "content": "Your previous response was not valid JSON. Return a JSON array only. No preamble. No markdown code fences."})
                raw_response_retry = _call_llm(url, api_key, payload)
                if not raw_response_retry:
                    continue
                cleaned_response = clean_json_response(raw_response_retry)
                try:
                    issues = json.loads(cleaned_response)
                except json.JSONDecodeError as exc:
                    log_error(logger, file_path, f"Failed to parse JSON on retry: {exc}")
                    continue

            if not isinstance(issues, list):
                log_error(logger, file_path, "LLM returned valid JSON, but it is not a JSON array.")
                continue

            _insert_ai_issues(conn, project_name, file_path, issues)
            # Add to set so we don't process it again if somehow listed twice
            processed_files.add(file_path)
            
            log_success(logger, file_path, f"Analyzed -> {len(issues)} issues found.")

        # ── Process Simple Files in Batches ──────────────────────────────────────────────
        unprocessed_simple_files = [f for f in simple_files if f["file_path"] not in processed_files]
        batches = [unprocessed_simple_files[i:i + batch_size] for i in range(0, len(unprocessed_simple_files), batch_size)]

        for batch in batches:
            if not batch:
                continue
                
            user_prompt_lines = []
            file_paths = []
            
            for file_row in batch:
                file_path = file_row["file_path"]
                file_paths.append(file_path)
                bundle = _file_bundle(conn, root, file_row)
                user_prompt_lines.append(f"File : {file_path}\n{json.dumps(bundle, ensure_ascii=False)}")
                
            system_prompt = """You are a Senior Frontend Architect reviewing multiple small Vue.js components. Analyze each separately. Focus ONLY on architectural issues. For every issue provide: exact line number, 3-5 line code snippet, concrete actionable recommendation. Return a JSON object where each key is the file_path and the value is an array of issues for that file. Return JSON only. No preamble. No markdown. Schema: {'src/components/A.vue': [{'issue_category': '...', 'description': '...', 'severity': 'High|Medium|Low', 'line_number': 0, 'code_snippet': '...', 'recommendation': '...'}], 'src/components/B.vue': []}"""
            
            user_prompt = "\n\n".join(user_prompt_lines)
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            
            raw_response = _call_llm(url, api_key, payload)
            if not raw_response:
                continue

            cleaned_response = clean_json_response(raw_response)
            
            try:
                results = json.loads(cleaned_response)
            except json.JSONDecodeError:
                payload["messages"].append({"role": "assistant", "content": raw_response})
                payload["messages"].append({"role": "user", "content": "Your previous response was not valid JSON. Return a JSON object only. No preamble. No markdown code fences."})
                raw_response_retry = _call_llm(url, api_key, payload)
                if not raw_response_retry:
                    continue
                cleaned_response = clean_json_response(raw_response_retry)
                try:
                    results = json.loads(cleaned_response)
                except json.JSONDecodeError as exc:
                    log_error(logger, "BATCH", f"Failed to parse JSON on retry: {exc}")
                    continue
                    
            if not isinstance(results, dict):
                log_error(logger, "BATCH", "LLM returned valid JSON, but it is not a JSON object.")
                continue
                
            total_issues_batch = 0
            for file_path, issues in results.items():
                if not isinstance(issues, list):
                    continue
                _insert_ai_issues(conn, project_name, file_path, issues)
                processed_files.add(file_path)
                total_issues_batch += len(issues)
                
            log_success(logger, "BATCH", f"Analyzed batch of {len(batch)} simple files -> {total_issues_batch} issues total.")
            
        logger.info("[AI Phase 2/3] Per-file analysis complete.")
            
    finally:
        conn.close()

if __name__ == "__main__":
    run_reporter()
