"""
ai_pipeline/ai_architecture_analyzer.py
---------------------------------------
Stage 7: AI Architecture Analyzer
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
from ai_pipeline.test_llm_connection import load_env_manual

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

def _get_ai_issues(root: Path, project_name: str) -> str:
    db_path = root / "audit_tool" / "audit_history.db"
    if not db_path.exists():
        return "No issues found."
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT file_path, phase, issue_category, description, severity, recommendation FROM ai_issues WHERE project_name = ? ORDER BY file_path, severity",
            (project_name,)
        )
        issues = cursor.fetchall()
        
        if not issues:
            return "No issues found."
            
        # Group by file
        grouped = {}
        for row in issues:
            fp = row['file_path']
            if fp not in grouped:
                grouped[fp] = []
            grouped[fp].append(row)
            
        output = []
        for fp, file_issues in grouped.items():
            output.append(f"File: {fp}")
            for iss in file_issues:
                output.append(f"  - [{str(iss['severity']).upper()}] {iss['issue_category']} ({iss['phase']}): {iss['description']}")
                if iss['recommendation']:
                    output.append(f"    Recommendation: {iss['recommendation']}")
            output.append("")
        return "\n".join(output)
    finally:
        conn.close()

def _get_summary_statistics(root: Path, project_name: str) -> str:
    db_path = root / "audit_tool" / "audit_history.db"
    if not db_path.exists():
        return "Database not found."
        
    conn = sqlite3.connect(str(db_path))
    try:
        # Total files scanned
        cursor = conn.execute("SELECT COUNT(id) FROM vue_files WHERE project_name = ?", (project_name,))
        total_files = cursor.fetchone()[0] or 0
        
        # Total files with issues
        cursor = conn.execute("SELECT COUNT(DISTINCT file_path) FROM ai_issues WHERE project_name = ?", (project_name,))
        files_with_issues = cursor.fetchone()[0] or 0
        
        # Severity counts
        cursor = conn.execute("SELECT severity, COUNT(*) FROM ai_issues WHERE project_name = ? GROUP BY severity", (project_name,))
        counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for row in cursor.fetchall():
            sev = str(row[0]) if row[0] else 'Medium'
            # Normalize severity casing
            if sev.lower() == 'high': sev = 'High'
            elif sev.lower() == 'medium': sev = 'Medium'
            elif sev.lower() == 'low': sev = 'Low'
            
            if sev in counts:
                counts[sev] += row[1]
            else:
                counts[sev] = row[1]
                
        return f"- Total files scanned: {total_files}\n- Total files with issues: {files_with_issues}\n- High severity issues: {counts['High']}\n- Medium severity issues: {counts['Medium']}\n- Low severity issues: {counts['Low']}"
    finally:
        conn.close()

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
        # Long timeout as this involves large context windows
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            response_dict = json.loads(raw)
            return (response_dict.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
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

def _update_audit_runs(root: Path, project_name: str, synthesis_text: str) -> None:
    db_path = root / "audit_tool" / "audit_history.db"
    conn = sqlite3.connect(str(db_path))
    try:
        # Check if row exists
        cursor = conn.execute("SELECT id FROM audit_runs WHERE project_name = ? ORDER BY id DESC LIMIT 1", (project_name,))
        row = cursor.fetchone()
        if row:
            # Update existing
            conn.execute(
                "UPDATE audit_runs SET synthesis_text = ?, status = 'complete', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (synthesis_text, row[0])
            )
        else:
            # Insert new safely
            conn.execute(
                "INSERT INTO audit_runs (project_name, current_phase, status, synthesis_text) VALUES (?, ?, ?, ?)",
                (project_name, 'report', 'complete', synthesis_text)
            )
        conn.commit()
    finally:
        conn.close()

def run_architecture_analyzer() -> None:
    logger.info("[AI Phase 3/3] Starting Architecture Synthesis...")
    
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
        logger.warning("skeleton_map.txt is empty. Aborting architecture analysis.")
        return
        
    issues_text = _get_ai_issues(root, project_name)
    stats_text = _get_summary_statistics(root, project_name)
    
    system_prompt = """You are a Senior Frontend Architect writing an executive architectural report for a Vue.js codebase. 
CRITICAL RULES:
1. You MUST respond STRICTLY IN ENGLISH. 
2. You MUST use EXACTLY the following 5 headings in ALL CAPS and nothing else.
3. DO NOT add any intro, outro, or conversational filler.
4. DO NOT use markdown hash marks (#) for the headings.

Required Headings and Formats:
HEALTH SCORE
(Score from 0 to 100. Two sentence justification)

TOP 5 CRITICAL COMPONENTS
(The 5 most problematic components and exactly why)

RECURRING PATTERNS
(Patterns appearing across multiple components. Be specific about counts)

PRIORITIZED RECOMMENDATIONS
(Numbered list. High priority first. Concrete and actionable)

SUGGESTED REFACTORING SEQUENCE
(In what order should the team fix things and why)"""

    user_prompt = f"Skeleton Map:\n{skeleton_map_text}\n\nAll Issues Found:\n{issues_text}\n\nStatistics:\n{stats_text}"

    url = _chat_completions_url(base_url)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    
    raw_response = _call_llm(url, api_key, payload)
    
    if not raw_response:
        log_error(logger, "LLM", "No response received from LLM.")
        return
        
    _update_audit_runs(root, project_name, raw_response)
    
    log_success(logger, "Synthesis", "[AI Phase 3/3] Synthesis complete and saved to database.")
    
if __name__ == "__main__":
    run_architecture_analyzer()
