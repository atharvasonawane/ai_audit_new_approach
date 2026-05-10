"""
ai_pipeline/ai_dependency_builder.py
------------------------------------
Stage 5: AI Dependency Graph Analyzer
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

def _get_project_name(root: Path) -> str:
    config_path = root / "audit_tool" / "project_config.yaml"
    if not config_path.exists():
        log_error(logger, str(config_path), "project_config.yaml not found.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("project", {}).get("name", "unknown_project")

def _read_skeleton_map(root: Path) -> str:
    skeleton_path = root / "skeleton_map.txt"
    if not skeleton_path.exists():
        log_error(logger, str(skeleton_path), "skeleton_map.txt not found. Please run the Scout first.")
        return ""
    return skeleton_path.read_text(encoding="utf-8", errors="replace")

def _get_component_relationships(root: Path, project_name: str) -> list[str]:
    db_path = root / "audit_tool" / "audit_history.db"
    if not db_path.exists():
        log_error(logger, str(db_path), "audit_history.db not found.")
        return []
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT parent_file, child_file FROM component_relationships WHERE project_name = ?",
            (project_name,)
        )
        relationships = []
        for row in cursor.fetchall():
            relationships.append(f"{row['parent_file']} -> {row['child_file']}")
        return relationships
    finally:
        conn.close()

def _chat_completions_url(base_url: str) -> str:
    u = (base_url or "").strip().rstrip("/")
    if u.endswith("/chat/completions"):
        return u
    return u + "/chat/completions"

def _call_llm(url: str, api_key: str, payload: dict) -> str:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "CodeAuditLibrarian/1.0")

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
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

def _insert_ai_issues(root: Path, project_name: str, issues: list[dict]) -> None:
    db_path = root / "audit_tool" / "audit_history.db"
    conn = sqlite3.connect(str(db_path))
    try:
        inserted_count = 0
        for issue in issues:
            affected_files = issue.get("affected_files", [])
            if isinstance(affected_files, list):
                file_path = ", ".join(affected_files)
            else:
                file_path = str(affected_files)
                
            raw_sev = issue.get("severity", "Medium")
            severity = str(raw_sev).capitalize() if raw_sev else "Medium"
            if severity not in ("High", "Medium", "Low"):
                severity = "Medium"
                
            conn.execute(
                """
                INSERT INTO ai_issues 
                (project_name, file_path, phase, issue_category, description, severity, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_name,
                    file_path,
                    'dependency',
                    issue.get("issue_category"),
                    issue.get("description"),
                    severity,
                    issue.get("recommendation")
                )
            )
            inserted_count += 1
        conn.commit()
    finally:
        conn.close()

def run_dependency_builder() -> None:
    logger.info("[AI Phase 1/3] Analyzing dependency graph...")
    
    root = _repo_root()
    load_env_manual(str(root / ".env"))
    
    # Use OPENWEBUI OR LLM configured keys
    base_url = os.getenv("OPENWEBUI_BASE_URL") or os.getenv("LLM_BASE_URL")
    api_key = os.getenv("OPENWEBUI_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    
    if not base_url or not api_key or not model:
        log_error(logger, ".env", "Missing OPENWEBUI_BASE_URL / OPENWEBUI_API_KEY / LLM_MODEL in .env.")
        return
        
    project_name = _get_project_name(root)
    skeleton_map_text = _read_skeleton_map(root)
    if not skeleton_map_text:
        logger.warning("skeleton_map.txt is empty. Aborting dependency analysis.")
        return
        
    relationships = _get_component_relationships(root, project_name)
    relationships_text = "\n".join(relationships) if relationships else "No relationships found."
    if not relationships:
        logger.warning("No component relationships found in database. Proceeding anyway, but results may be limited.")
    
    system_prompt = """You are a Senior Frontend Architect analyzing a Vue.js component dependency graph.

You will receive:
1. A skeleton map of the entire codebase with metrics per file
2. A list of component relationships (who imports who)

Identify these dependency problems:
- Prop Drilling Chain: props passed down 3+ levels
- God Component: imports 8+ other components
- Circular Dependency: A imports B which imports A
- Orphaned Component: no parent imports it
- Over-coupled Service: imported by 10+ components

Return a JSON array only. No preamble. No explanation. No markdown code fences.

Schema:
[{
  "issue_category": "Prop Drilling Chain",
  "description": "Specific explanation",
  "severity": "High",
  "affected_files": ["src/components/A.vue"],
  "recommendation": "Concrete fix"
}]"""

    user_prompt = f"""Skeleton Map:
{skeleton_map_text}

Component Relationships:
{relationships_text}"""

    url = _chat_completions_url(base_url)
    
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
        log_error(logger, "LLM", "No response received from LLM.")
        return
        
    cleaned_response = clean_json_response(raw_response)
    
    try:
        issues = json.loads(cleaned_response)
    except json.JSONDecodeError:
        logger.info("[AI Phase 1/3] Invalid JSON received. Executing ONE retry.")
        # Retry once
        payload["messages"].append({"role": "assistant", "content": raw_response})
        payload["messages"].append({
            "role": "user", 
            "content": "Your previous response was not valid JSON. Return a JSON array only. No preamble. No markdown code fences."
        })
        
        raw_response_retry = _call_llm(url, api_key, payload)
        if not raw_response_retry:
             log_error(logger, "LLM", "No response received from LLM on retry.")
             return
             
        cleaned_response_retry = clean_json_response(raw_response_retry)
        
        try:
            issues = json.loads(cleaned_response_retry)
        except json.JSONDecodeError as exc:
            log_error(logger, "LLM", f"Failed to parse JSON on retry. Aborting. {exc}")
            return
            
    if not isinstance(issues, list):
        log_error(logger, "LLM", "LLM returned valid JSON, but it is not a JSON array. Aborting.")
        return
        
    _insert_ai_issues(root, project_name, issues)
    
    logger.info(f"[AI Phase 1/3] Complete. {len(issues)} dependency issues found.")
    
if __name__ == "__main__":
    run_dependency_builder()
