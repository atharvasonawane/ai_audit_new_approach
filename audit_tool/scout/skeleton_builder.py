"""
scout/skeleton_builder.py
------------------------
Stage 3: Generate skeleton_map.txt from SQLite Scout facts.

Output format (one line per file):
  src/components/Checkout.vue | 340 lines | 12 methods | 8 APIs (1 in loop) | nesting:5 | complexity:14 | eslint:[no-unused-vars, alt-text]
"""

from __future__ import annotations

from pathlib import Path

import yaml

from audit_tool.db.db_init import get_connection
from audit_tool.utils.logger import get_logger, log_success


logger = get_logger(__name__)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "project_config.yaml"


def _load_project_name(config_path: Path) -> str:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    project = raw.get("project", {}) or {}
    return str(project.get("name") or "unnamed-project")


def _project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def build_skeleton_map(config_path: str | Path | None = None) -> Path:
    cfg_path = Path(config_path) if config_path else _default_config_path()
    project_name = _load_project_name(cfg_path)
    project_root = _project_root_from_config(cfg_path)

    out_path = project_root / "skeleton_map.txt"

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT
                id,
                file_path,
                script_lines,
                template_lines,
                style_lines,
                methods,
                api_total,
                api_in_loop,
                max_nesting_depth,
                cyclomatic_complexity
            FROM vue_files
            WHERE project_name = ?
            ORDER BY file_path ASC
            """,
            (project_name,),
        )
        rows = cursor.fetchall()

        lines: list[str] = []
        for row in rows:
            file_path = row["file_path"]
            total_lines = int((row["script_lines"] or 0) + (row["template_lines"] or 0) + (row["style_lines"] or 0))
            methods = int(row["methods"] or 0)
            api_total = int(row["api_total"] or 0)
            api_in_loop = int(row["api_in_loop"] or 0)
            nesting = int(row["max_nesting_depth"] or 0)
            complexity = int(row["cyclomatic_complexity"] or 0)

            flag_cursor = conn.execute(
                """
                SELECT DISTINCT rule
                FROM file_flags
                WHERE project_name = ? AND file_path = ? AND rule IS NOT NULL AND rule <> ''
                """,
                (project_name, file_path),
            )
            rules = sorted({r["rule"] for r in flag_cursor.fetchall() if r["rule"]})
            rules_str = ", ".join(rules)

            lines.append(
                f"{file_path} | {total_lines} lines | {methods} methods | "
                f"{api_total} APIs ({api_in_loop} in loop) | nesting:{nesting} | "
                f"complexity:{complexity} | eslint:[{rules_str}]"
            )

        out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        log_success(logger, str(out_path), f"Skeleton map written (lines={len(lines)} project={project_name})")
        return out_path
    finally:
        conn.close()


if __name__ == "__main__":
    build_skeleton_map()
