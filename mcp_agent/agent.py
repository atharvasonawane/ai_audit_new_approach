import asyncio
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from openai import OpenAI

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

from db.db_init import DEFAULT_DB_PATH
from db.db_writer import upsert_ai_issue

try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except ImportError as exc:
    raise ImportError(
        "MCP client libraries are required. Install the 'mcp' package."
    ) from exc


CONFIG_PATH = PROJECT_ROOT / "audit_tool" / "config" / "project_config.yaml"
SERVER_PATH = PROJECT_ROOT / "mcp_agent" / "server.py"

logger = logging.getLogger("mcp_agent")

SCRIPT_LINES_COMPLEX_THRESHOLD = 150
SIMPLE_FILE_BATCH_SIZE = 8

# Appended to user prompt on second LLM attempt when JSON parsing fails
CRITICAL_JSON_RETRY_SUFFIX = (
    "\n\nCRITICAL: Your previous response was not valid JSON. "
    "You MUST return ONLY a valid JSON array. No preamble. No markdown code fences."
)


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    return {}


def _normalize_path(file_path: str, base_path: str) -> str:
    if base_path:
        try:
            from extractors.path_utils import normalize_path

            return normalize_path(file_path, base_path)
        except Exception:
            pass
    return file_path.replace("\\", "/")


def _resolve_base_url(base_url: str) -> str:
    if not base_url:
        raise ValueError("OPENWEBUI_BASE_URL is required")
    if base_url.endswith("/api/v1"):
        return base_url
    if base_url.endswith("/v1"):
        return base_url[: -len("/v1")] + "/api/v1"
    return base_url.rstrip("/") + "/api/v1"


def _clean_json_string(raw: str) -> str:
    if raw is None:
        return ""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """
    Extract JSON array from text, handling padding/conversational content.

    Strategy:
    1. Try direct parse on cleaned text
    2. Find first [ and last ] in cleaned text
    3. Extract block between them
    4. Parse that block
    5. If all fails, print first 200 chars for debugging
    """
    clean_text = _clean_json_string(text)

    # First try direct parsing
    try:
        data = json.loads(clean_text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Find first [ and last ]
    start_idx = clean_text.find("[")
    end_idx = clean_text.rfind("]")

    if start_idx < 0 or end_idx < 0 or end_idx <= start_idx:
        print(
            f"ERROR: Could not find JSON array brackets. First 200 chars of raw_content:\n{clean_text[:200]}"
        )
        raise ValueError("LLM output is not a JSON array")

    # Extract the block from first [ to last ]
    json_str = clean_text[start_idx : end_idx + 1]

    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: Failed to parse extracted JSON block. First 200 chars of raw_content:\n{clean_text[:200]}"
        )
        raise ValueError(f"LLM output is not a JSON array: {exc}") from exc

    raise ValueError("LLM output is not a JSON array")


def _normalize_issue(issue: Any) -> Dict[str, Any]:
    """
    Normalize issue object, handling both camelCase and snake_case field names.
    Standardizes to: issue_category, title, description, severity, line_number, recommendation
    """
    if not isinstance(issue, dict):
        return {}

    # Handle line_number - may come as int, string, or camelCase field
    line_num = issue.get("line_number") or issue.get("lineNumber")
    if isinstance(line_num, str):
        try:
            line_num = int(line_num)
        except (ValueError, TypeError):
            line_num = 0
    elif not isinstance(line_num, int):
        line_num = 0

    normalized = {
        "issue_category": issue.get("issue_category")
        or issue.get("issueCategory")
        or "unknown",
        "title": issue.get("title") or "Untitled",
        "description": issue.get("description") or issue.get("message") or "",
        "severity": issue.get("severity") or "Low",
        "line_number": line_num,
        "recommendation": issue.get("recommendation") or issue.get("fix") or "",
    }
    return normalized


def _normalize_severity(value: Any) -> str:
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"high", "medium", "low"}:
            return cleaned.title()
    return "Low"


def _read_raw_source(file_path: str, base_path: Optional[str]) -> str:
    path = Path(file_path)
    if not path.exists() and base_path:
        candidate = Path(base_path) / file_path
        if candidate.exists():
            path = candidate
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_snippet(lines: List[str], line_number: int) -> str:
    start = max(1, line_number - 2)
    end = min(len(lines), line_number + 2)
    snippet_lines = []
    for idx in range(start, end + 1):
        prefix = "► " if idx == line_number else "  "
        snippet_lines.append(f"{prefix}{idx}: {lines[idx - 1]}")
    return "\n".join(snippet_lines)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "text"):
        return getattr(value, "text")
    dump_fn = getattr(value, "model_dump", None)
    if callable(dump_fn):
        try:
            return dump_fn()
        except Exception:
            pass
    return value


def _db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _fetch_in_progress_run(
    db_path: Path, project_name: str
) -> Optional[sqlite3.Row]:
    with _db_connect(db_path) as conn:
        return conn.execute(
            """
            SELECT id, project_name, started_at, status, last_completed_file
            FROM audit_runs
            WHERE project_name = ? AND status = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """,
            (project_name,),
        ).fetchone()


def _mark_run_failed(db_path: Path, run_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with _db_connect(db_path) as conn:
        conn.execute(
            """
            UPDATE audit_runs
            SET status = 'failed', completed_at = ?
            WHERE id = ?
            """,
            (now, run_id),
        )
        conn.commit()


def _insert_audit_run_in_progress(db_path: Path, project_name: str) -> int:
    started = datetime.utcnow().isoformat()
    with _db_connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO audit_runs (project_name, started_at, status, last_completed_file)
            VALUES (?, ?, 'in_progress', NULL)
            """,
            (project_name, started),
        )
        conn.commit()
        return int(cur.lastrowid)


def _update_run_last_file(db_path: Path, run_id: int, last_file: str) -> None:
    with _db_connect(db_path) as conn:
        conn.execute(
            "UPDATE audit_runs SET last_completed_file = ? WHERE id = ?",
            (last_file, run_id),
        )
        conn.commit()


def _complete_audit_run(db_path: Path, run_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with _db_connect(db_path) as conn:
        conn.execute(
            """
            UPDATE audit_runs
            SET status = 'completed', completed_at = ?
            WHERE id = ?
            """,
            (now, run_id),
        )
        conn.commit()


def _finalize_audit_run_with_synthesis(
    db_path: Path, run_id: int, synthesis_text: str
) -> None:
    now = datetime.utcnow().isoformat()
    with _db_connect(db_path) as conn:
        conn.execute(
            """
            UPDATE audit_runs
            SET status = 'completed',
                synthesis_text = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (synthesis_text, now, run_id),
        )
        conn.commit()


def _fetch_in_progress_run_id(db_path: Path, project_name: str) -> Optional[int]:
    with _db_connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id FROM audit_runs
            WHERE project_name = ? AND status = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """,
            (project_name,),
        ).fetchone()
    return int(row["id"]) if row else None


def _fetch_executive_synthesis_context(
    db_path: Path, project_name: str
) -> Dict[str, Any]:
    """Aggregate stats and worst offenders for executive synthesis (direct SQLite)."""
    with _db_connect(db_path) as conn:
        total_row = conn.execute(
            "SELECT COUNT(*) AS n FROM vue_files WHERE project_name = ?",
            (project_name,),
        ).fetchone()
        total_files = int(total_row["n"] or 0)

        eslint_row = conn.execute(
            """
            SELECT COALESCE(SUM(eslint_flag_count), 0) AS n
            FROM vue_files
            WHERE project_name = ?
            """,
            (project_name,),
        ).fetchone()
        total_eslint_flags = int(eslint_row["n"] or 0)

        sev_rows = conn.execute(
            """
            SELECT severity, COUNT(*) AS cnt
            FROM ai_issues
            WHERE project_name = ? AND phase = 'file_analysis'
            GROUP BY severity
            """,
            (project_name,),
        ).fetchall()
        ai_by_severity: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        for r in sev_rows:
            key = r["severity"] or "Low"
            if key not in ai_by_severity:
                key = "Low"
            ai_by_severity[key] = int(r["cnt"] or 0)

        offender_rows = conn.execute(
            """
            SELECT
                vf.file_path,
                COALESCE(vf.eslint_flag_count, 0) AS eslint_count,
                COALESCE(ai.cnt, 0) AS ai_issue_count,
                COALESCE(vf.eslint_flag_count, 0) + COALESCE(ai.cnt, 0) AS combined_score
            FROM vue_files vf
            LEFT JOIN (
                SELECT file_path, COUNT(*) AS cnt
                FROM ai_issues
                WHERE project_name = ? AND phase = 'file_analysis'
                GROUP BY file_path
            ) ai ON ai.file_path = vf.file_path
            WHERE vf.project_name = ?
            ORDER BY combined_score DESC
            LIMIT 10
            """,
            (project_name, project_name),
        ).fetchall()

    worst_offenders: List[Dict[str, Any]] = [
        {
            "file_path": r["file_path"],
            "eslint_flag_count": int(r["eslint_count"] or 0),
            "ai_issue_count": int(r["ai_issue_count"] or 0),
            "combined_score": int(r["combined_score"] or 0),
        }
        for r in offender_rows
    ]

    return {
        "project_name": project_name,
        "total_files": total_files,
        "total_eslint_flags": total_eslint_flags,
        "ai_issues_by_severity": ai_by_severity,
        "ai_issues_total": sum(ai_by_severity.values()),
        "worst_offenders": worst_offenders,
    }


async def generate_executive_synthesis(project_name: str) -> None:
    """
    Phase 3 — Executive synthesis: macro context from SQLite, one LLM call (plain text),
    persist to audit_runs.synthesis_text and mark run completed.
    """
    cfg = _load_config()
    db_path = Path(cfg.get("db", {}).get("path", DEFAULT_DB_PATH))
    run_id = _fetch_in_progress_run_id(db_path, project_name)
    if run_id is None:
        logger.warning(
            "generate_executive_synthesis: no in_progress audit_run for project %s",
            project_name,
        )
        return

    ctx = _fetch_executive_synthesis_context(db_path, project_name)
    if ctx["total_files"] == 0:
        _finalize_audit_run_with_synthesis(
            db_path,
            run_id,
            "No scanned files were found in `vue_files` for this project. "
            "Run the scout phase (`run_audit.py`) first, then re-run the AI agent.",
        )
        print("[Executive synthesis] No files in DB — run finalized with placeholder text.")
        return

    base_url = _resolve_base_url(os.getenv("OPENWEBUI_BASE_URL", ""))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    llm = OpenAI(base_url=base_url, api_key=api_key)

    system_prompt = (
        "You are a Principal Software Architect preparing an executive summary for a development team "
        "about a Vue.js codebase audit. Write in clear, professional prose. Markdown headings and bullets "
        "are encouraged. Do NOT output JSON or code fences. "
        "Your response must cover: "
        "(1) Overall Health — high-level assessment using the provided metrics; "
        "(2) Critical Risk Areas — prioritize files and themes called out in the data; "
        "(3) Prioritized Refactoring Sequence — concrete, ordered recommendations. "
        "Reference specific file paths from the data when relevant. Be honest if the codebase looks healthy."
    )

    user_prompt = (
        "Use the following audit metrics (from our SQLite database after automated and AI file analysis). "
        "Write the executive summary now.\n\n"
        + json.dumps(ctx, indent=2, ensure_ascii=True)
    )

    synthesis_text = ""
    try:
        response = llm.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gemma3:latest"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
        )
        if response and getattr(response, "choices", None):
            synthesis_text = (response.choices[0].message.content or "").strip()
        if not synthesis_text:
            raise RuntimeError("LLM returned empty executive summary")
    except Exception as exc:
        logger.exception("Executive synthesis LLM call failed: %s", exc)
        synthesis_text = (
            "## Executive synthesis unavailable\n\n"
            f"Automatic generation failed: {exc}\n\n"
            "### Recovered metrics (raw)\n\n"
            f"```\n{json.dumps(ctx, indent=2, ensure_ascii=True)}\n```"
        )

    _finalize_audit_run_with_synthesis(db_path, run_id, synthesis_text)
    print(
        f"[Executive synthesis] Saved to audit_runs id={run_id} "
        f"({len(synthesis_text)} chars); status=completed."
    )


def _fetch_files_done_for_run(
    db_path: Path, project_name: str, run_started_at: str
) -> Set[str]:
    with _db_connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT file_path
            FROM ai_issues
            WHERE project_name = ?
              AND phase = 'file_analysis'
              AND created_at >= ?
            """,
            (project_name, run_started_at),
        ).fetchall()
    return {r["file_path"] for r in rows}


def _fetch_vue_files_with_script_lines(
    db_path: Path, project_name: str
) -> List[Tuple[str, int]]:
    with _db_connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT file_path, COALESCE(script_lines, 0) AS script_lines
            FROM vue_files
            WHERE project_name = ?
            ORDER BY file_path
            """,
            (project_name,),
        ).fetchall()
    return [(r["file_path"], int(r["script_lines"] or 0)) for r in rows]


def _split_complex_simple(
    paths_with_lines: List[Tuple[str, int]],
) -> Tuple[List[str], List[str]]:
    complex_files: List[str] = []
    simple_files: List[str] = []
    for fp, sl in paths_with_lines:
        if sl >= SCRIPT_LINES_COMPLEX_THRESHOLD:
            complex_files.append(fp)
        else:
            simple_files.append(fp)
    return complex_files, simple_files


def _validate_and_write_issues_for_file(
    file_path: str,
    issues: List[Any],
    base_path: Optional[str],
    project_name: str,
    db_path: Path,
) -> List[Dict[str, Any]]:
    raw_source = _read_raw_source(file_path, base_path)
    lines = raw_source.splitlines()

    normalized_path = _normalize_path(file_path, base_path or "")
    vue_file_id = None
    with _db_connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM vue_files WHERE project_name = ? AND file_path = ?",
            (project_name, normalized_path),
        ).fetchone()
        if row:
            vue_file_id = row["id"]

    if not vue_file_id:
        raise RuntimeError("File was not found in sqlite vue_files table")

    results: List[Dict[str, Any]] = []
    for idx, issue in enumerate(issues):
        # Normalize the issue object to handle different field name conventions
        normalized = _normalize_issue(issue)
        if not normalized:
            logger.warning(
                "Malformed AI issue skipped for %s (expected JSON object, got %s): %r",
                normalized_path,
                type(issue).__name__,
                issue,
            )
            continue

        line_number = normalized.get("line_number")
        if (
            normalized.get("issue_category") == "unknown"
            and normalized.get("title") == "Untitled"
            and (
                not isinstance(line_number, int)
                or line_number < 1
            )
        ):
            logger.warning(
                "Malformed AI issue skipped for %s (placeholder category/title, "
                "no valid line_number): %r",
                normalized_path,
                issue,
            )
            continue


        if not isinstance(line_number, int):
            continue
        if line_number < 1 or line_number > len(lines):
            continue

        severity = _normalize_severity(normalized.get("severity"))
        snippet = _extract_snippet(lines, line_number)
        created_at = datetime.utcnow().isoformat()

        record = {
            "vue_file_id": vue_file_id,
            "project_name": project_name,
            "file_path": normalized_path,
            "phase": "file_analysis",
            "issue_category": normalized.get("issue_category", ""),
            "title": normalized.get("title", ""),
            "description": normalized.get("description", ""),
            "severity": severity,
            "line_number": line_number,
            "code_snippet": snippet,
            "recommendation": normalized.get("recommendation", ""),
            "created_at": created_at,
        }

        upsert_ai_issue(record, db_path=db_path)
        results.append(record)

    print(f"✓ Wrote {len(results)} issues to database")
    return results


class MCPToolClient:
    def __init__(self, server_path: Path):
        self._server_path = server_path
        self._session: Optional[ClientSession] = None
        self._client_ctx = None

    async def __aenter__(self) -> "MCPToolClient":
        params = StdioServerParameters(
            command=str(Path(sys.executable)), args=[str(self._server_path)]
        )
        self._client_ctx = stdio_client(params)
        reader, writer = await self._client_ctx.__aenter__()
        self._session = ClientSession(reader, writer)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session:
            try:
                await self._session.__aexit__(exc_type, exc, tb)
            except Exception as close_exc:
                logger.warning("MCP session close failed: %s", close_exc)
        if self._client_ctx:
            try:
                await self._client_ctx.__aexit__(exc_type, exc, tb)
            except Exception as close_exc:
                logger.warning("MCP client context close failed: %s", close_exc)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self._session:
            raise RuntimeError("MCP session not initialized")
        result = await self._session.call_tool(name, arguments)
        content = getattr(result, "content", result)
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and "text" in first:
                text = first.get("text") or ""
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
            if hasattr(first, "text"):
                return first.text
        return content


async def _run_tool_loop(
    client: MCPToolClient,
    llm: OpenAI,
    file_path: str,
    prompt_suffix: str = "",
) -> str:
    if os.getenv("OPENWEBUI_DISABLE_TOOLS", "1") == "1":
        return await _run_prompt_only(client, llm, file_path, prompt_suffix=prompt_suffix)

    tool_defs = [
        {
            "type": "function",
            "function": {
                "name": "get_all_files",
                "description": "List all scanned file paths.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_file_metrics",
                "description": "Return metrics for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_file_flags",
                "description": "Return ESLint flags for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_file_api_calls",
                "description": "Return API calls for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_accessibility_defects",
                "description": "Return accessibility defects for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_raw_source",
                "description": "Read raw source code for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_worst_offenders",
                "description": "List the worst offenders.",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_project_summary",
                "description": "Return project summary stats.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_component_relationships",
                "description": "Return component relationships for a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
    ]

    system_prompt = (
        "You are a Senior Frontend Architect analyzing a Vue file. "
        "Use the available tools to fetch metrics, flags, API calls, accessibility defects, "
        "raw source, and relationships as needed. "
        "Your entire response must be a single valid JSON array. Begin your response with [ and end it with ]. "
        "Say absolutely nothing else. "
        "Each issue must include: issue_category, title, description, severity, line_number, recommendation. "
        "Do NOT include any code snippets in the response."
    )

    user_prompt = (
        "Analyze the file and return your findings as a JSON array. "
        f"Target file_path: {file_path}"
    )
    if prompt_suffix:
        user_prompt += prompt_suffix

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    while True:
        try:
            raw_response = llm.chat.completions.with_raw_response.create(
                model=os.getenv("LLM_MODEL", "gemma3:latest"),
                messages=messages,
                tools=tool_defs,
                tool_choice="auto",
                temperature=0.2,
            )
        except Exception as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        try:
            response = raw_response.parse()
        except Exception as exc:
            raw_text = getattr(raw_response, "text", None)
            if callable(raw_text):
                raw_text = raw_text()
            raise RuntimeError(
                f"LLM response could not be parsed. Raw: {raw_text}"
            ) from exc

        if not response or not getattr(response, "choices", None):
            raw_text = getattr(raw_response, "text", None)
            if callable(raw_text):
                raw_text = raw_text()
            raise RuntimeError(f"LLM returned no choices. Raw response: {raw_text}")

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            return message.content or "[]"

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await client.call_tool(call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.function.name,
                    "content": json.dumps(result, ensure_ascii=True),
                }
            )


async def _run_prompt_only(
    client: MCPToolClient,
    llm: OpenAI,
    file_path: str,
    prompt_suffix: str = "",
) -> str:
    context = {
        "file_path": file_path,
        "metrics": await client.call_tool("get_file_metrics", {"file_path": file_path}),
        "eslint_flags": await client.call_tool(
            "get_file_flags", {"file_path": file_path}
        ),
        "api_calls": await client.call_tool(
            "get_file_api_calls", {"file_path": file_path}
        ),
        "accessibility_defects": await client.call_tool(
            "get_accessibility_defects", {"file_path": file_path}
        ),
        "relationships": await client.call_tool(
            "get_component_relationships", {"file_path": file_path}
        ),
        "raw_source": await client.call_tool(
            "get_raw_source", {"file_path": file_path}
        ),
    }

    context = _to_jsonable(context)

    system_prompt = (
        "You are a JSON generator. You output ONLY valid JSON. No other text. "
        "When given code and context, you extract issues and return them as a JSON array. "
        "EXACT REQUIRED FORMAT: "
        '[{"issue_category":"string","title":"string","description":"string","severity":"High|Medium|Low","line_number":number,"recommendation":"string"},...] '
        "Field names MUST be: issue_category, title, description, severity, line_number, recommendation. "
        "If no issues found: return [] "
        "DO NOT EXPLAIN. DO NOT ADD PROSE. ONLY JSON."
    )

    user_prompt = (
        "CODE AND CONTEXT (JSON):\n" + json.dumps(context, ensure_ascii=True) + "\n\n"
        "Return ONLY a JSON array of issues. No other text."
    )
    if prompt_suffix:
        user_prompt += prompt_suffix

    try:
        raw_response = llm.chat.completions.with_raw_response.create(
            model=os.getenv("LLM_MODEL", "gemma3:latest"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    raw_content = None
    response = None
    try:
        response = raw_response.parse()
    except Exception:
        pass

    if response and getattr(response, "choices", None):
        raw_content = response.choices[0].message.content

    if raw_content is None:
        raw_text = getattr(raw_response, "text", None)
        if callable(raw_text):
            raw_text = raw_text()
        raw_content = raw_text

    if raw_content is None:
        raise RuntimeError("LLM returned no content.")

        print(
            f"DEBUG: Raw LLM response (first 500 chars):\n{raw_content[:500]}\n---END---\n"
        )
    return _clean_json_string(raw_content)


async def _run_batch_prompt_only(
    client: MCPToolClient,
    llm: OpenAI,
    file_paths: List[str],
    prompt_suffix: str = "",
) -> str:
    files_payload: List[Dict[str, Any]] = []
    for fp in file_paths:
        entry = {
            "file_path": fp,
            "metrics": await client.call_tool("get_file_metrics", {"file_path": fp}),
            "eslint_flags": await client.call_tool("get_file_flags", {"file_path": fp}),
            "api_calls": await client.call_tool(
                "get_file_api_calls", {"file_path": fp}
            ),
            "accessibility_defects": await client.call_tool(
                "get_accessibility_defects", {"file_path": fp}
            ),
            "relationships": await client.call_tool(
                "get_component_relationships", {"file_path": fp}
            ),
            "raw_source": await client.call_tool("get_raw_source", {"file_path": fp}),
        }
        files_payload.append(_to_jsonable(entry))

    system_prompt = (
        "You are a JSON generator. You output ONLY valid JSON. No other text. "
        "You analyze multiple Vue files at once. Return a SINGLE JSON array combining issues from ALL files. "
        "Each object MUST include file_path (exactly matching one of the input file_path values) plus: "
        "issue_category, title, description, severity (High|Medium|Low), line_number, recommendation. "
        "If a file has no issues, omit any entries for that file (or none) — the array may be empty. "
        "DO NOT include code snippets. DO NOT EXPLAIN. ONLY the JSON array."
    )

    user_prompt = (
        "FILES AND CONTEXT (JSON array, one object per file):\n"
        + json.dumps(files_payload, ensure_ascii=True)
        + "\n\nReturn ONLY one JSON array of issues. Every issue must include file_path."
    )
    if prompt_suffix:
        user_prompt += prompt_suffix

    try:
        raw_response = llm.chat.completions.with_raw_response.create(
            model=os.getenv("LLM_MODEL", "gemma3:latest"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    raw_content = None
    response = None
    try:
        response = raw_response.parse()
    except Exception:
        pass

    if response and getattr(response, "choices", None):
        raw_content = response.choices[0].message.content

    if raw_content is None:
        raw_text = getattr(raw_response, "text", None)
        if callable(raw_text):
            raw_text = raw_text()
        raw_content = raw_text

    if raw_content is None:
        raise RuntimeError("LLM returned no content.")

    return _clean_json_string(raw_content)


def _partition_batch_issues_by_file(
    issues: List[Any],
    batch_paths: Set[str],
    base_path: Optional[str],
) -> Dict[str, List[Dict[str, Any]]]:
    by_file: Dict[str, List[Dict[str, Any]]] = {fp: [] for fp in batch_paths}
    for issue in issues:
        if not isinstance(issue, dict):
            logger.warning(
                "Malformed batch issue skipped (expected JSON object, got %s): %r",
                type(issue).__name__,
                issue,
            )
            continue
        fp_raw = issue.get("file_path") or issue.get("filePath")
        if not fp_raw:
            continue
        normalized = _normalize_path(str(fp_raw), base_path or "")
        if normalized not in batch_paths:
            continue
        by_file[normalized].append(issue)
    return by_file


async def _run_full_codebase_async(
    run_id: int,
    complex_files: List[str],
    simple_files: List[str],
    skip_files: Set[str],
    base_path: Optional[str],
    project_name: str,
    db_path: Path,
) -> None:
    base_url = _resolve_base_url(os.getenv("OPENWEBUI_BASE_URL", ""))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    llm = OpenAI(base_url=base_url, api_key=api_key)

    async with MCPToolClient(SERVER_PATH) as client:
        n_complex = len(complex_files)
        for idx, fp in enumerate(complex_files, start=1):
            if fp in skip_files:
                continue
            display_name = Path(fp).name
            print(f"[Complex {idx}/{n_complex}] Processing {display_name}...")
            issues: Optional[List[Dict[str, Any]]] = None
            for attempt in range(2):
                suffix = CRITICAL_JSON_RETRY_SUFFIX if attempt == 1 else ""
                try:
                    raw = await _run_tool_loop(client, llm, fp, prompt_suffix=suffix)
                    print(f"DEBUG: Raw LLM response (first 300 chars):\n{raw[:300]}")
                    issues = _extract_json_array(raw)
                    print(f"Parsed {len(issues)} issues")
                    break
                except (ValueError, json.JSONDecodeError):
                    if attempt == 0:
                        continue
                    logger.error(
                        f"Failed to parse JSON for {fp} after retry. Skipping."
                    )
                    issues = None
                    break

            if issues is None:
                continue

            _validate_and_write_issues_for_file(
                fp, issues, base_path, project_name, db_path
            )
            _update_run_last_file(db_path, run_id, fp)

        n_simple = len(simple_files)
        if n_simple:
            num_batches = (n_simple + SIMPLE_FILE_BATCH_SIZE - 1) // SIMPLE_FILE_BATCH_SIZE
        else:
            num_batches = 0

        for batch_start in range(0, n_simple, SIMPLE_FILE_BATCH_SIZE):
            batch = simple_files[batch_start : batch_start + SIMPLE_FILE_BATCH_SIZE]
            batch_num = batch_start // SIMPLE_FILE_BATCH_SIZE + 1
            batch_to_run = [f for f in batch if f not in skip_files]
            if not batch_to_run:
                continue
            n_in_batch = len(batch_to_run)
            print(
                f"[Batch {batch_num}/{num_batches}] Processing {n_in_batch} simple files..."
            )
            all_issues: Optional[List[Dict[str, Any]]] = None
            for attempt in range(2):
                suffix = CRITICAL_JSON_RETRY_SUFFIX if attempt == 1 else ""
                try:
                    raw = await _run_batch_prompt_only(
                        client, llm, batch_to_run, prompt_suffix=suffix
                    )
                    print(
                        f"DEBUG: Raw batch LLM response (first 300 chars):\n{raw[:300]}"
                    )
                    all_issues = _extract_json_array(raw)
                    print(f"Parsed {len(all_issues)} issues (batch)")
                    break
                except (ValueError, json.JSONDecodeError):
                    if attempt == 0:
                        continue
                    file_path = ", ".join(batch_to_run)
                    logger.error(
                        f"Failed to parse JSON for {file_path} after retry. Skipping."
                    )
                    all_issues = None
                    break

            if all_issues is None:
                continue

            batch_set = set(batch_to_run)
            by_file = _partition_batch_issues_by_file(
                all_issues, batch_set, base_path
            )
            for fp in batch_to_run:
                file_issues = by_file.get(fp, [])
                _validate_and_write_issues_for_file(
                    fp, file_issues, base_path, project_name, db_path
                )
                _update_run_last_file(db_path, run_id, fp)


def analyze_single_file(file_path: str) -> List[Dict[str, Any]]:
    cfg = _load_config()
    base_path = cfg.get("base_path")
    project_name = cfg.get("project_name", "default")
    db_path = Path(cfg.get("db", {}).get("path", DEFAULT_DB_PATH))

    base_url = _resolve_base_url(os.getenv("OPENWEBUI_BASE_URL", ""))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    llm = OpenAI(base_url=base_url, api_key=api_key)

    async def _run() -> List[Dict[str, Any]]:
        async with MCPToolClient(SERVER_PATH) as client:
            issues: Optional[List[Dict[str, Any]]] = None
            for attempt in range(2):
                suffix = CRITICAL_JSON_RETRY_SUFFIX if attempt == 1 else ""
                try:
                    raw = await _run_tool_loop(
                        client, llm, file_path, prompt_suffix=suffix
                    )
                    print(f"DEBUG: Raw LLM response (first 300 chars):\n{raw[:300]}")
                    issues = _extract_json_array(raw)
                    print(f"Parsed {len(issues)} issues")
                    break
                except (ValueError, json.JSONDecodeError):
                    if attempt == 0:
                        continue
                    logger.error(
                        f"Failed to parse JSON for {file_path} after retry. Skipping."
                    )
                    issues = None
                    break

            if issues is None:
                return []

            return _validate_and_write_issues_for_file(
                file_path, issues, base_path, project_name, db_path
            )

    return asyncio.run(_run())


def analyze_file_batch(file_paths: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyze up to 8 (or fewer) files in one LLM call. Returns written records per file_path.
    """
    cfg = _load_config()
    base_path = cfg.get("base_path")
    project_name = cfg.get("project_name", "default")
    db_path = Path(cfg.get("db", {}).get("path", DEFAULT_DB_PATH))

    base_url = _resolve_base_url(os.getenv("OPENWEBUI_BASE_URL", ""))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    llm = OpenAI(base_url=base_url, api_key=api_key)

    async def _run() -> Dict[str, List[Dict[str, Any]]]:
        async with MCPToolClient(SERVER_PATH) as client:
            all_issues: Optional[List[Dict[str, Any]]] = None
            for attempt in range(2):
                suffix = CRITICAL_JSON_RETRY_SUFFIX if attempt == 1 else ""
                try:
                    raw = await _run_batch_prompt_only(
                        client, llm, file_paths, prompt_suffix=suffix
                    )
                    print(
                        f"DEBUG: Raw batch LLM response (first 300 chars):\n{raw[:300]}"
                    )
                    all_issues = _extract_json_array(raw)
                    print(f"Parsed {len(all_issues)} issues (batch)")
                    break
                except (ValueError, json.JSONDecodeError):
                    if attempt == 0:
                        continue
                    file_path = ", ".join(file_paths)
                    logger.error(
                        f"Failed to parse JSON for {file_path} after retry. Skipping."
                    )
                    all_issues = None
                    break

            if all_issues is None:
                return {fp: [] for fp in file_paths}

            batch_set = set(file_paths)
            by_file = _partition_batch_issues_by_file(
                all_issues, batch_set, base_path
            )
            out: Dict[str, List[Dict[str, Any]]] = {}
            for fp in file_paths:
                out[fp] = _validate_and_write_issues_for_file(
                    fp, by_file.get(fp, []), base_path, project_name, db_path
                )
            return out

    return asyncio.run(_run())


def run_full_codebase_audit() -> int:
    """
    Process all vue_files for the configured project: complex files one-by-one,
    simple files in batches. Handles crash recovery via audit_runs + ai_issues.
    Returns audit run id.
    """
    cfg = _load_config()
    base_path = cfg.get("base_path")
    project_name = cfg.get("project_name", "default")
    db_path = Path(cfg.get("db", {}).get("path", DEFAULT_DB_PATH))

    interrupted = _fetch_in_progress_run(db_path, project_name)
    skip_files: Set[str] = set()
    run_id: int

    if interrupted:
        choice = input("Found interrupted run. Resume? (y/n): ").strip().lower()
        if choice == "y":
            run_id = int(interrupted["id"])
            skip_files = _fetch_files_done_for_run(
                db_path, project_name, interrupted["started_at"]
            )
            print(
                f"[AI Agent] Resuming run {run_id}; "
                f"skipping {len(skip_files)} file(s) already recorded for this run."
            )
        else:
            _mark_run_failed(db_path, int(interrupted["id"]))
            run_id = _insert_audit_run_in_progress(db_path, project_name)
            print(f"[AI Agent] Started new audit run id={run_id}.")
    else:
        run_id = _insert_audit_run_in_progress(db_path, project_name)
        print(f"[AI Agent] Started audit run id={run_id}.")

    paths_rows = _fetch_vue_files_with_script_lines(db_path, project_name)
    if not paths_rows:
        print("[AI Agent] No files in vue_files for this project.")
        asyncio.run(generate_executive_synthesis(project_name))
        return run_id

    complex_files, simple_files = _split_complex_simple(paths_rows)
    print(
        f"[AI Agent] Queue: {len(complex_files)} complex (script_lines>={SCRIPT_LINES_COMPLEX_THRESHOLD}), "
        f"{len(simple_files)} simple."
    )

    async def _pipeline() -> None:
        await _run_full_codebase_async(
            run_id,
            complex_files,
            simple_files,
            skip_files,
            base_path,
            project_name,
            db_path,
        )
        await generate_executive_synthesis(project_name)

    try:
        asyncio.run(_pipeline())
    except BaseException:
        logger.exception("Audit run %s aborted before completion", run_id)
        raise

    print(f"[AI Agent] Audit run {run_id} completed successfully (including executive synthesis).")
    return run_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("LLM AGENT: Full codebase analysis + executive synthesis (Stages 4–5)")
    print("=" * 60)

    try:
        run_full_codebase_audit()
    except Exception as e:
        print(f"\n✗ Analysis failed: {e}")
        import traceback

        traceback.print_exc()
