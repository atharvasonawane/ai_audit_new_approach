import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.db_init import DEFAULT_DB_PATH

try:
    import yaml
except ImportError:
    yaml = None

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError("FastMCP is required. Install the FastMCP package.") from exc


DB_PATH = Path(os.getenv("AUDIT_DB_PATH", DEFAULT_DB_PATH))
CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "audit_tool"
    / "config"
    / "project_config.yaml"
)
BASE_PATH = None

if yaml and CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
            BASE_PATH = cfg.get("base_path") or None
    except Exception:
        BASE_PATH = None

mcp = FastMCP("code-audit-librarian")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _fetch_all(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        cursor = conn.execute(sql, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def _fetch_one(sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    with _get_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        return dict(row) if row else None


@mcp.tool()
def get_all_files() -> List[str]:
    rows = _fetch_all("SELECT file_path FROM vue_files ORDER BY file_path")
    return [row["file_path"] for row in rows]


@mcp.tool()
def get_file_metrics(file_path: str) -> Optional[Dict[str, Any]]:
    return _fetch_one("SELECT * FROM vue_files WHERE file_path = ?", (file_path,))


@mcp.tool()
def get_file_flags(file_path: str) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT ff.*
        FROM file_flags ff
        JOIN vue_files vf ON vf.id = ff.vue_file_id
        WHERE vf.file_path = ? AND ff.category = 'eslint'
        ORDER BY ff.line_number ASC
        """,
        (file_path,),
    )


@mcp.tool()
def get_file_api_calls(file_path: str) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT ac.*
        FROM api_calls ac
        JOIN vue_files vf ON vf.id = ac.vue_file_id
        WHERE vf.file_path = ?
        ORDER BY ac.line_number ASC
        """,
        (file_path,),
    )


@mcp.tool()
def get_accessibility_defects(file_path: str) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT ad.*
        FROM accessibility_defects ad
        JOIN vue_files vf ON vf.id = ad.vue_file_id
        WHERE vf.file_path = ?
        ORDER BY ad.line_number ASC
        """,
        (file_path,),
    )


@mcp.tool()
def get_raw_source(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists() and not path.is_absolute() and BASE_PATH:
        candidate = Path(BASE_PATH) / file_path
        if candidate.exists():
            path = candidate

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_worst_offenders(limit: int = 10) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            vf.file_path,
            vf.eslint_flag_count,
            vf.max_nesting_depth,
            COALESCE(SUM(CASE WHEN ac.in_loop = 1 THEN 1 ELSE 0 END), 0) AS api_in_loop
        FROM vue_files vf
        LEFT JOIN api_calls ac ON ac.vue_file_id = vf.id
        GROUP BY vf.id
        ORDER BY
            COALESCE(vf.eslint_flag_count, 0)
            + COALESCE(api_in_loop, 0)
            + COALESCE(vf.max_nesting_depth, 0) DESC
        LIMIT ?
        """,
        (limit,),
    )


@mcp.tool()
def get_project_summary() -> Dict[str, Any]:
    summary = _fetch_one(
        """
        SELECT
            COUNT(*) AS total_files,
            COALESCE(SUM(vf.eslint_flag_count), 0) AS total_flags,
            (SELECT COUNT(*) FROM api_calls) AS total_api_calls,
            COALESCE(AVG(vf.max_nesting_depth), 0) AS average_nesting_depth
        FROM vue_files vf
        """
    )
    return summary or {}


@mcp.tool()
def get_component_relationships(file_path: str) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT * FROM component_relationships
        WHERE parent_file = ? OR child_file = ?
        ORDER BY parent_file, child_file
        """,
        (file_path, file_path),
    )


if __name__ == "__main__":
    mcp.run()
