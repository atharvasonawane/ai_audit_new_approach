"""
ai_pipeline/test_llm_connection.py
---------------------------------
Stage 4 verification: LLM JSON Validation (Critical Gate).

Dependency-free version (stdlib only):
  - Manually loads .env into os.environ
  - Calls an OpenAI-compatible endpoint via urllib
  - Logs raw model output and validates strict JSON parsing

All output routes through audit_tool/utils/logger.py (no print()).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_tool.utils.logger import get_logger, log_error, log_success


logger = get_logger(__name__)


def load_env_manual(filepath: str = ".env") -> None:
    """
    Minimal .env loader (no external deps).
    - Ignores blank lines and comments (# ...)
    - Supports KEY=VALUE
    - Strips surrounding quotes from VALUE if present
    - Populates os.environ (does not overwrite existing keys)
    """
    path = Path(filepath)
    if not path.exists():
        log_error(logger, str(path), ".env not found")
        return

    try:
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            os.environ.setdefault(key, value)
    except Exception as exc:
        log_error(logger, str(path), f"Failed to load .env: {exc}")


def clean_json_response(raw_text: str) -> str:
    """
    Strip markdown code fences (```json ... ```) and whitespace.
    LLMs often wrap JSON in markdown even when instructed not to.
    """
    text = (raw_text or "").strip()
    if not text:
        return ""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _db_path(root: Path) -> Path:
    return root / "audit_tool" / "audit_history.db"


def _connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _pick_one_file(conn: sqlite3.Connection, project_name: str) -> sqlite3.Row | None:
    # Prefer a SMALL file to keep the validation payload tiny (avoid 413 / token limits).
    cursor = conn.execute(
        """
        SELECT *
        FROM vue_files
        WHERE project_name = ? AND script_lines > 5 AND script_lines < 50
        LIMIT 1
        """,
        (project_name,),
    )
    row = cursor.fetchone()
    if row:
        return row

    # Fallback: anything.
    cursor = conn.execute(
        """
        SELECT *
        FROM vue_files
        WHERE project_name = ?
        LIMIT 1
        """,
        (project_name,),
    )
    return cursor.fetchone()


def _load_file_source(root: Path, file_path: str) -> str:
    abs_path = (root / Path(file_path)).resolve()
    try:
        return abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        log_error(logger, file_path, f"Failed to read source from disk: {exc}")
        raise


def _file_bundle(conn: sqlite3.Connection, root: Path, file_row: sqlite3.Row, *, truncate_source: bool) -> dict[str, Any]:
    file_path = str(file_row["file_path"])
    source_code = _load_file_source(root, file_path)
    if truncate_source:
        lines = source_code.splitlines()
        source_code = "\n".join(lines[:100]) + "\n...[TRUNCATED FOR TEST]"

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

    imports_cursor = conn.execute(
        """
        SELECT child_file
        FROM component_relationships
        WHERE project_name = ? AND parent_file = ?
        ORDER BY child_file ASC
        """,
        (file_row["project_name"], file_path),
    )
    imports = [r["child_file"] for r in imports_cursor.fetchall()]

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
        "imports": imports,
        "eslint_flags": eslint_flags,
        "api_calls": api_calls,
    }


def _system_prompt_complex_individual() -> str:
    # From CODE_AUDIT_LIBRARIAN_MASTER.md (System prompt for complex files - individual),
    # with the mandatory strict ending line appended.
    prompt = """You are a Senior Frontend Architect reviewing a single Vue.js component.
You have the full source code plus AST metrics and ESLint findings.

Do NOT report ESLint syntax violations — those are captured separately.

Focus ONLY on architectural issues:
- State Management Bloat: unrelated state crowded into data()
- Prop Drilling: receiving props only to pass them to children
- Component Over-responsibility: doing too many jobs
- API Flow Issues: calls in wrong lifecycle hooks or inside loops
- Logic Misplacement: business logic that belongs in a service or composable
- Performance Risks: expensive operations in watchers or computed

For every issue you MUST provide:
- Exact line number
- 3 to 5 line code snippet showing the problem
- Concrete actionable recommendation

Return a JSON array only. No preamble. No markdown.

Schema:
[{
  "issue_category": "State Management Bloat",
  "description": "Specific explanation for this file",
  "severity": "High",
  "line_number": 112,
  "code_snippet": "relevant lines from source",
  "recommendation": "Concrete fix"
}]

If no issues found, return: []
"""
    return prompt.rstrip() + "\nReturn a JSON array only. No preamble. No explanation. No markdown code fences."


def _chat_completions_url(base_url: str) -> str:
    u = (base_url or "").strip().rstrip("/")
    if u.endswith("/chat/completions"):
        return u
    return u + "/chat/completions"

def _models_url(base_url: str) -> str:
    u = (base_url or "").strip().rstrip("/")
    if u.endswith("/models"):
        return u
    return u + "/models"


def _post_chat_completion(url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "CodeAuditLibrarian/1.0")

    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

def _get_models(url: str, api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "CodeAuditLibrarian/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def main() -> None:
    root = _repo_root()
    load_env_manual(str(root / ".env"))

    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not base_url or not api_key or not model:
        log_error(
            logger,
            ".env",
            "Missing LLM_BASE_URL / LLM_API_KEY / LLM_MODEL. Set them in repo-root .env and retry.",
        )
        return

    # Log config presence (never log the API key itself).
    logger.info(
        "LLM config loaded: base_url=%s model=%s api_key_present=%s",
        base_url,
        model,
        "yes" if bool(api_key and api_key.strip()) else "no",
    )

    db_path = _db_path(root)
    if not db_path.exists():
        log_error(logger, str(db_path), "audit_history.db not found. Run Stage 3 scanner first.")
        return

    conn = _connect_db(db_path)
    try:
        configured_project = os.getenv("AUDIT_PROJECT_NAME")  # optional override
        if configured_project:
            project_name = configured_project
        else:
            cur = conn.execute(
                "SELECT project_name, COUNT(*) AS c FROM vue_files GROUP BY project_name ORDER BY c DESC"
            )
            row = cur.fetchone()
            project_name = row["project_name"] if row else None

        if not project_name:
            log_error(logger, str(db_path), "No vue_files rows found. Run Stage 3 scanner first.")
            return

        file_row = _pick_one_file(conn, project_name)
        if not file_row:
            log_error(logger, project_name, "No files found for this project_name in vue_files.")
            return

        truncate_source = not (int(file_row["script_lines"] or 0) > 5 and int(file_row["script_lines"] or 0) < 50)
        bundle = _file_bundle(conn, root, file_row, truncate_source=truncate_source)
        if truncate_source:
            logger.warning("Selected file is not small; source_code truncated to first 100 lines for validation test.")
    finally:
        conn.close()

    system_prompt = _system_prompt_complex_individual()
    user_prompt = f"File: {bundle['file_path']}\n{json.dumps(bundle, ensure_ascii=False)}"

    url = _chat_completions_url(base_url)
    models_url = _models_url(base_url)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    # Preflight: verify connectivity/auth by calling GET /models.
    try:
        models_resp = _get_models(models_url, api_key)
        log_success(logger, models_url, "Preflight OK (/models reachable)")
        logger.info("Preflight /models keys: %s", list(models_resp.keys())[:10])
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<no body>"
        log_error(logger, models_url, f"Preflight HTTPError {exc.code}: {body}")
        return
    except Exception as exc:
        log_error(logger, models_url, f"Preflight request failed: {exc}")
        return

    try:
        response_dict = _post_chat_completion(url, api_key, payload)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<no body>"
        log_error(logger, url, f"HTTPError {exc.code}: {body}")
        return
    except Exception as exc:
        log_error(logger, url, f"Request failed: {exc}")
        return

    try:
        raw = (response_dict["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        log_error(logger, url, f"Unexpected response shape: {exc}")
        logger.info("RAW API RESPONSE JSON:\n%s", json.dumps(response_dict, ensure_ascii=False))
        return

    logger.info("RAW LLM RESPONSE (%s):\n%s", bundle["file_path"], raw)

    cleaned = clean_json_response(raw)
    try:
        parsed = json.loads(cleaned)
        log_success(logger, str(bundle["file_path"]), "JSON successfully parsed!")
        logger.info("Parsed JSON type: %s", type(parsed).__name__)
    except Exception as exc:
        log_error(logger, str(bundle["file_path"]), f"Failed to parse JSON: {exc}")


if __name__ == "__main__":
    main()
