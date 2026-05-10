"""
scout/scanner.py
----------------
Stage 3 orchestrator: scan an entire codebase in parallel, cache unchanged files,
and write deterministic Scout facts into SQLite.

Critical rules:
  - All output routes through audit_tool/utils/logger.py (no print()).
  - Parsing/extraction uses the Stage 2 extractors (tree-sitter based for JS).
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

# Silence noisy third-party FutureWarnings that bypass our logger (keeps output readable).
warnings.filterwarnings(
    "ignore",
    message=r".*Language\(path, name\) is deprecated.*",
    category=FutureWarning,
)

from audit_tool.db.db_init import get_connection, initialise_database
from audit_tool.db import db_writer
from audit_tool.utils.logger import get_logger, log_error, log_skipped, log_success

from audit_tool.scout.vue_parser import split_vue_sfc
from audit_tool.scout.metrics_extractor import extract_template_metrics, extract_script_metrics
from audit_tool.scout.import_extractor import extract_imports
from audit_tool.scout.api_extractor import extract_api_calls
from audit_tool.scout.eslint_runner import run_eslint


logger = get_logger(__name__)


@dataclass(frozen=True)
class _ScanConfig:
    project_name: str
    project_root: Path
    target_paths: list[str]
    exclude_paths: list[str]
    file_extensions: set[str]
    parallel_workers: int


def _default_config_path() -> Path:
    # audit_tool/scout/scanner.py -> audit_tool/project_config.yaml
    return Path(__file__).resolve().parent.parent / "project_config.yaml"


def _load_config(config_path: Path) -> _ScanConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    project = raw.get("project", {}) or {}
    scout = raw.get("scout", {}) or {}

    project_name = str(project.get("name") or "unnamed-project")
    target_paths = list(project.get("target_paths") or [])
    exclude_paths = list(project.get("exclude_paths") or [])
    file_extensions = set((scout.get("file_extensions") or [".vue", ".js"]))
    parallel_workers = int(scout.get("parallel_workers") or 8)

    project_root = config_path.resolve().parent.parent

    return _ScanConfig(
        project_name=project_name,
        project_root=project_root,
        target_paths=target_paths,
        exclude_paths=exclude_paths,
        file_extensions=file_extensions,
        parallel_workers=max(1, parallel_workers),
    )


def _path_is_excluded(path: Path, exclude_segments: set[str]) -> bool:
    # Robust absolute-path filtering: if any directory component matches an excluded segment,
    # skip the entire subtree/file. Works across OS path separators.
    lower_parts = {p.lower() for p in path.parts}
    if any(seg in lower_parts for seg in exclude_segments):
        return True

    # Also handle rare cases where excluded directories appear in a joined segment.
    path_str = str(path).lower()
    for seg in exclude_segments:
        if f"/{seg}/" in path_str or f"\\{seg}\\" in path_str:
            return True
    return False


def _iter_eligible_files(cfg: _ScanConfig) -> Iterable[Path]:
    exclude_segments = {p.lower() for p in cfg.exclude_paths}

    for rel_target in cfg.target_paths:
        abs_target = (cfg.project_root / rel_target).resolve()
        if not abs_target.exists():
            logger.warning("Target path missing, skipping: %s", abs_target)
            continue

        for root, dirs, files in os.walk(abs_target):
            root_path = Path(root)
            if _path_is_excluded(root_path, exclude_segments):
                dirs[:] = []
                continue

            dirs[:] = [d for d in dirs if d.lower() not in exclude_segments]

            for filename in files:
                file_path = root_path / filename
                if _path_is_excluded(file_path, exclude_segments):
                    continue
                if file_path.suffix.lower() not in cfg.file_extensions:
                    continue
                yield file_path


def _sha256_of_file(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _db_get_cached_file(conn, *, project_name: str, file_path: str) -> tuple[str | None, float | None]:
    cursor = conn.execute(
        "SELECT file_hash, last_modified FROM vue_files WHERE project_name = ? AND file_path = ?",
        (project_name, file_path),
    )
    row = cursor.fetchone()
    if not row:
        return None, None
    return row["file_hash"], row["last_modified"]


def _process_file(cfg: _ScanConfig, abs_file_path: Path, *, force: bool) -> bool:
    rel_file_path = abs_file_path.resolve().relative_to(cfg.project_root).as_posix()

    try:
        mtime = os.path.getmtime(abs_file_path)
        file_hash = _sha256_of_file(abs_file_path)

        conn = get_connection()
        try:
            if not force:
                cached_hash, cached_mtime = _db_get_cached_file(
                    conn, project_name=cfg.project_name, file_path=rel_file_path
                )
                if cached_hash == file_hash and cached_mtime == mtime:
                    log_skipped(logger, rel_file_path, "Unchanged (Cache Hit)")
                    return True

            try:
                with open(abs_file_path, "r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()
            except Exception as exc:
                log_error(logger, rel_file_path, f"Read failed: {exc}")
                return False

            template_code = ""
            script_code = ""
            style_code = ""
            if abs_file_path.suffix.lower() == ".vue":
                blocks = split_vue_sfc(source_code)
                template_code = blocks.get("template", "")
                script_code = blocks.get("script", "")
                style_code = blocks.get("style", "")
            else:
                script_code = source_code

            script_lines = len(script_code.strip().splitlines()) if script_code.strip() else 0
            template_lines = len(template_code.strip().splitlines()) if template_code.strip() else 0
            style_lines = len(style_code.strip().splitlines()) if style_code.strip() else 0

            try:
                template_metrics = extract_template_metrics(template_code)
                script_metrics = extract_script_metrics(script_code)
                imports = extract_imports(script_code)
            except Exception as exc:
                log_error(logger, rel_file_path, f"Tree-sitter parse failed: {exc}")
                return False

            script_line_offset = 0
            if abs_file_path.suffix.lower() == ".vue" and script_code:
                idx = source_code.find(script_code)
                if idx != -1:
                    script_line_offset = source_code[:idx].count("\n")

            try:
                api_calls = extract_api_calls(script_code, line_offset=script_line_offset)
            except Exception as exc:
                log_error(logger, rel_file_path, f"Tree-sitter parse failed: {exc}")
                return False
            api_total = len(api_calls)
            api_in_mounted = sum(1 for call in api_calls if call.get("in_mounted"))
            api_in_loop = sum(1 for call in api_calls if call.get("in_loop"))

            eslint_flags = run_eslint(str(abs_file_path)) if abs_file_path.suffix.lower() == ".vue" else []

            vue_file_id = db_writer.upsert_vue_file(
                conn,
                project_name=cfg.project_name,
                file_path=rel_file_path,
                file_hash=file_hash,
                script_lines=script_lines,
                template_lines=template_lines,
                style_lines=style_lines,
                methods=int(script_metrics.get("methods", 0)),
                computed=int(script_metrics.get("computed", 0)),
                watchers=int(script_metrics.get("watchers", 0)),
                props=int(script_metrics.get("props", 0)),
                emits=int(script_metrics.get("emits", 0)),
                api_total=api_total,
                api_in_mounted=api_in_mounted,
                api_in_loop=api_in_loop,
                max_nesting_depth=int(template_metrics.get("max_nesting_depth", 0)),
                cyclomatic_complexity=int(script_metrics.get("cyclomatic_complexity", 0)),
                eslint_flag_count=len(eslint_flags),
                script_setup=bool("setup" in source_code and abs_file_path.suffix.lower() == ".vue"),
                template_only=bool(abs_file_path.suffix.lower() == ".vue" and not script_code.strip()),
                typescript_detected=bool("lang=\"ts\"" in source_code or "lang='ts'" in source_code),
                last_modified=mtime,
            )

            if vue_file_id is None:
                log_error(logger, rel_file_path, "DB write failed (upsert_vue_file returned None)")
                return False

            db_writer.delete_component_relationships(
                conn, project_name=cfg.project_name, parent_file=rel_file_path
            )
            for imp in imports:
                db_writer.upsert_component_relationship(
                    conn,
                    project_name=cfg.project_name,
                    parent_file=rel_file_path,
                    child_file=imp,
                    relationship_type="import",
                )

            db_writer.delete_file_flags(conn, project_name=cfg.project_name, file_path=rel_file_path)
            for flag in eslint_flags:
                db_writer.insert_file_flag(
                    conn,
                    vue_file_id=vue_file_id,
                    project_name=cfg.project_name,
                    file_path=rel_file_path,
                    rule=flag.get("rule"),
                    message=flag.get("message"),
                    severity=flag.get("severity"),
                    line_number=int(flag.get("line_number", 0) or 0),
                    column_number=int(flag.get("column_number", 0) or 0),
                )

            db_writer.delete_api_calls(conn, project_name=cfg.project_name, file_path=rel_file_path)
            for call in api_calls:
                db_writer.insert_api_call(
                    conn,
                    vue_file_id=vue_file_id,
                    project_name=cfg.project_name,
                    file_path=rel_file_path,
                    api_type=call.get("api_type"),
                    method_name=call.get("method_name"),
                    endpoint=call.get("endpoint"),
                    in_mounted=bool(call.get("in_mounted")),
                    in_loop=bool(call.get("in_loop")),
                    line_number=int(call.get("line_number", 0) or 0),
                )

            conn.commit()
            log_success(logger, rel_file_path, "Parsed & Saved")
            return True
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as exc:
        log_error(logger, rel_file_path, f"Extraction failed: {exc}")
        return False


def run_scan(config_path: str | Path | None = None) -> None:
    run_scan_with_options(config_path=config_path, force=False, reset_project_cache=False)


def _reset_project_cache_in_db(*, project_name: str) -> None:
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM file_flags WHERE project_name = ?", (project_name,))
            conn.execute("DELETE FROM api_calls WHERE project_name = ?", (project_name,))
            conn.execute("DELETE FROM component_relationships WHERE project_name = ?", (project_name,))
            conn.execute("DELETE FROM vue_files WHERE project_name = ?", (project_name,))
        log_success(logger, project_name, "Project cache cleared (SQLite rows deleted)")
    finally:
        conn.close()


def run_scan_with_options(
    *,
    config_path: str | Path | None = None,
    force: bool = False,
    reset_project_cache: bool = False,
) -> None:
    cfg_path = Path(config_path) if config_path else _default_config_path()
    cfg = _load_config(cfg_path)

    logger.info("Stage 3 scan starting. project=%s root=%s", cfg.project_name, cfg.project_root)
    initialise_database()

    if reset_project_cache:
        _reset_project_cache_in_db(project_name=cfg.project_name)

    eligible_files = sorted({p.resolve() for p in _iter_eligible_files(cfg)})
    logger.info("Eligible files found: %s", len(eligible_files))

    if not eligible_files:
        logger.warning("No eligible files found. Check project_config.yaml target_paths.")
        return

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.parallel_workers) as executor:
        if force:
            log_success(logger, cfg.project_name, "Force mode enabled (ignoring cache)")

        future_to_file = {
            executor.submit(_process_file, cfg, path, force=force): path for path in eligible_files
        }
        for future in concurrent.futures.as_completed(future_to_file):
            abs_path = future_to_file[future]
            try:
                rel_path = abs_path.relative_to(cfg.project_root).as_posix()
            except Exception:
                rel_path = str(abs_path)
            try:
                ok = future.result()
                if not ok:
                    failures += 1
                    log_error(logger, rel_path, "Worker reported failure")
            except Exception as exc:
                failures += 1
                log_error(logger, rel_path, f"Unhandled worker exception: {exc}")

    logger.info("Stage 3 scan complete. files=%s failures=%s", len(eligible_files), failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Audit Librarian - Stage 3 Scout Scanner")
    parser.add_argument("--config", default=None, help="Path to project_config.yaml (optional)")
    parser.add_argument("--force", action="store_true", help="Force rescan all files (ignore cache)")
    parser.add_argument(
        "--reset-project-cache",
        action="store_true",
        help="Delete all Scout rows for the configured project_name before scanning",
    )
    args = parser.parse_args()

    run_scan_with_options(
        config_path=args.config,
        force=bool(args.force),
        reset_project_cache=bool(args.reset_project_cache),
    )
