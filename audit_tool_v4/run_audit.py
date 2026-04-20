"""
run_audit.py — V4 Modernized Pipeline Orchestrator
===================================================
Implements Section 3 (Pipeline Execution Flow) of MASTER_ARCHITECTURE.md.

Phase 1 : Parallel Node.js execution via concurrent.futures ThreadPoolExecutor
Phase 2 : Raw JSON captured from each tool's stdout (normalization in Phase 3)
Phase 3 : Scoring & Penalties            (TODO — Phase 3 adapter step)
Phase 4 : Database ingestion             (TODO — Phase 3 adapter step)

Windows note: Node.js CLI tools in node_modules/.bin/ are .cmd wrappers on
Windows. This orchestrator auto-resolves the correct executable via
_resolve_bin(), so it works on both Windows and Unix.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent          # audit_tool_v4/
CONFIG_PATH = BASE / "config" / "project_config.yaml"
BIN_DIR     = BASE / "node_modules" / ".bin"
RAW_DIR     = BASE / "raw_outputs"           # raw JSON dumps from each tool

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s %(name)s -- %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger("run_audit_v4")


# ─────────────────────────────────────────────────────────────────────────────
# Config loading
# ─────────────────────────────────────────────────────────────────────────────
def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        sys.exit(1)

    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    load_dotenv(BASE.parent / ".env")      # project-level .env
    if "db" not in cfg:
        cfg["db"] = {}
    cfg["db"]["host"]     = os.getenv("MYSQL_HOST",     cfg["db"].get("host",     "localhost"))
    cfg["db"]["port"]     = int(os.getenv("MYSQL_PORT", cfg["db"].get("port",     3306)))
    cfg["db"]["user"]     = os.getenv("MYSQL_USER",     cfg["db"].get("user",     "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv("MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db"))
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# Binary resolver — handles Windows .cmd wrappers transparently
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_bin(name: str) -> str:
    """
    Return the absolute path to a node_modules/.bin/ executable.
    On Windows the actual runnable file is '<name>.cmd'; on Unix it is '<name>'.
    Falls back to the bare name so the OS PATH is tried last.
    """
    for candidate in [
        BIN_DIR / f"{name}.cmd",   # Windows
        BIN_DIR / name,            # Unix
    ]:
        if candidate.exists():
            return str(candidate)
    logger.warning("Binary '%s' not found in %s — falling back to PATH.", name, BIN_DIR)
    return name


# ─────────────────────────────────────────────────────────────────────────────
# ToolResult — structured return from each runner
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ToolResult:
    tool:        str
    status:      str                   # "ok" | "error" | "timeout" | "parse_error"
    returncode:  int        = 0
    raw_json:    Any        = None     # parsed JSON object (list or dict)
    raw_text:    str        = ""       # raw stdout if JSON parse failed
    stderr:      str        = ""
    elapsed_s:   float      = 0.0
    output_file: str        = ""       # path where raw JSON was saved

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Generic subprocess runner
# ─────────────────────────────────────────────────────────────────────────────
def _run_tool(
    tool_name:   str,
    cmd:         list[str],
    *,
    timeout:     int  = 300,
    cwd:         str  = "",
    allow_nonzero: bool = True,    # ESLint returns 1 when findings exist — that's normal
) -> ToolResult:
    """
    Run a CLI command, capture stdout+stderr, parse stdout as JSON.

    Args:
        tool_name:     Human label for this tool (used in logging + output filenames).
        cmd:           Full command list, e.g. ["path/to/eslint", ".", "--format", "json"].
        timeout:       Max seconds to wait before declaring timeout.
        cwd:           Working directory for the subprocess.
        allow_nonzero: If True, non-zero exit code is not treated as an error (for linters
                       that exit 1 when they find violations).

    Returns:
        ToolResult with all captured data.
    """
    logger.info("[%s] Starting: %s", tool_name, " ".join(cmd[:4]) + " ...")
    t0 = time.perf_counter()

    try:
        proc = subprocess.run(
            cmd,
            capture_output = True,
            text           = True,
            encoding       = "utf-8",
            errors         = "replace",
            timeout        = timeout,
            cwd            = cwd or None,
            shell          = False,
        )
    except subprocess.TimeoutExpired:
        logger.error("[%s] TIMEOUT after %ds.", tool_name, timeout)
        return ToolResult(tool=tool_name, status="timeout", elapsed_s=timeout)
    except FileNotFoundError as exc:
        logger.error("[%s] Binary not found: %s", tool_name, exc)
        return ToolResult(tool=tool_name, status="error", raw_text=str(exc))

    elapsed = round(time.perf_counter() - t0, 2)
    stdout  = proc.stdout.strip()
    stderr  = proc.stderr.strip()

    if proc.returncode != 0 and not allow_nonzero:
        logger.error("[%s] Non-zero exit %d:\n%s", tool_name, proc.returncode, stderr[:500])
        return ToolResult(
            tool       = tool_name,
            status     = "error",
            returncode = proc.returncode,
            raw_text   = stdout,
            stderr     = stderr,
            elapsed_s  = elapsed,
        )

    # ── Parse stdout as JSON ──────────────────────────────────────────────────
    if not stdout:
        logger.warning("[%s] Empty stdout (exit=%d).", tool_name, proc.returncode)
        return ToolResult(
            tool       = tool_name,
            status     = "ok" if (proc.returncode == 0 or allow_nonzero) else "error",
            returncode = proc.returncode,
            raw_json   = [],
            raw_text   = "",
            stderr     = stderr,
            elapsed_s  = elapsed,
        )

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.warning("[%s] stdout is not valid JSON (%s). Saving raw text.", tool_name, exc)
        return ToolResult(
            tool       = tool_name,
            status     = "parse_error",
            returncode = proc.returncode,
            raw_text   = stdout,
            stderr     = stderr,
            elapsed_s  = elapsed,
        )

    logger.info("[%s] ✓ Done in %.1fs (exit=%d).", tool_name, elapsed, proc.returncode)
    return ToolResult(
        tool       = tool_name,
        status     = "ok",
        returncode = proc.returncode,
        raw_json   = parsed,
        stderr     = stderr,
        elapsed_s  = elapsed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual tool runners — one function per tool
# Each returns a ToolResult and saves raw JSON to raw_outputs/<tool>.json
# ─────────────────────────────────────────────────────────────────────────────

def run_eslint(base_path: str, v4_root: str) -> ToolResult:
    """
    ESLint with vue-eslint-parser + eslint-plugin-vue + vuejs-accessibility.
    Covers: Parsing, Syntax/Quality, Accessibility (three tool rows in one pass).
    ESLint exits 1 when findings exist — that's not an error.
    """
    eslint_cfg = str(Path(v4_root) / ".eslintrc.js")
    cmd = [
        _resolve_bin("eslint"),
        base_path,
        "--ext", ".vue,.js,.ts",
        "--format", "json",
        "--no-eslintrc",
        "--config", eslint_cfg,
    ]
    return _run_tool("eslint", cmd, allow_nonzero=True)


def run_stylelint(base_path: str, v4_root: str) -> ToolResult:
    """
    Stylelint — CSS quality inside .vue <style> blocks and standalone .css files.
    Stylelint exits 1 on warnings/errors — allowed.
    """
    style_cfg = str(Path(v4_root) / ".stylelintrc.json")
    pattern   = f"{base_path}/**/*.{{vue,css,scss}}"
    cmd = [
        _resolve_bin("stylelint"),
        pattern,
        "--config", style_cfg,
        "--formatter", "json",
        "--allow-empty-input",
    ]
    return _run_tool("stylelint", cmd, allow_nonzero=True)


def run_cspell(base_path: str, v4_root: str) -> ToolResult:
    """
    CSpell — orthography/spelling check on visible text in .vue/.js/.ts files.
    Uses the project-level cspell.json config.
    """
    cspell_cfg = str(Path(v4_root) / "cspell.json")
    pattern    = f"{base_path}/**/*.{{vue,js,ts}}"
    cmd = [
        _resolve_bin("cspell"),
        "lint",
        "--config", cspell_cfg,
        "--reporter", "json",
        "--no-progress",
        pattern,
    ]
    return _run_tool("cspell", cmd, allow_nonzero=True)


def run_vue_mess_detector(base_path: str) -> ToolResult:
    """
    vue-mess-detector — Vue-specific complexity smells (supplementary).
    Note: JSON output format may vary across versions (0.x is unstable).
    """
    cmd = [
        _resolve_bin("vue-mess-detector"),
        "analyze",
        base_path,
        "--output", "json",
    ]
    return _run_tool("vue-mess-detector", cmd, allow_nonzero=True)


def run_dependency_cruiser(base_path: str) -> ToolResult:
    """
    dependency-cruiser — import graph and circular dependency detection.
    """
    cmd = [
        _resolve_bin("depcruise"),
        base_path,
        "--output-type", "json",
        "--exclude", "node_modules",
    ]
    return _run_tool("dependency-cruiser", cmd, allow_nonzero=True)


def run_jscpd(base_path: str) -> ToolResult:
    """
    jscpd — copy/paste duplication across .vue/.js/.ts files.
    Output goes to stdout via --reporters console-json (jscpd v4 style).
    """
    cmd = [
        _resolve_bin("jscpd"),
        base_path,
        "--reporters", "json",
        "--output", str(RAW_DIR),   # jscpd writes jscpd-report.json here
        "--ignore", "**/node_modules/**,**/dist/**",
        "--silent",
    ]
    # jscpd writes output file rather than stdout — run and then read the file
    result = _run_tool("jscpd", cmd, allow_nonzero=True)
    if result.raw_json is None:
        report_file = RAW_DIR / "jscpd-report.json"
        if report_file.exists():
            try:
                result.raw_json = json.loads(report_file.read_text(encoding="utf-8"))
                result.status   = "ok"
                logger.info("[jscpd] Loaded report from %s", report_file)
            except Exception as exc:
                logger.warning("[jscpd] Could not read report file: %s", exc)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Raw output saver
# ─────────────────────────────────────────────────────────────────────────────
def _save_raw(result: ToolResult) -> None:
    """Persist the raw JSON (or text) from a ToolResult to raw_outputs/<tool>.json."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = result.tool.replace("-", "_").replace(" ", "_")
    out_path  = RAW_DIR / f"{safe_name}.json"

    if result.raw_json is not None:
        payload = result.raw_json
    else:
        payload = {"status": result.status, "raw_text": result.raw_text, "stderr": result.stderr}

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)

    result.output_file = str(out_path)
    logger.info("[%s] Raw output → %s", result.tool, out_path.name)


# ─────────────────────────────────────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────────────────────────────────────
def _print_summary(results: list[ToolResult], total_elapsed: float) -> None:
    print()
    print("=" * 70)
    print("  V4 PIPELINE — PHASE 1 CAPTURE SUMMARY")
    print("=" * 70)
    print(f"  {'Tool':<25} {'Status':<14} {'Time':>6}s  {'Findings / Info'}")
    print("  " + "-" * 66)

    for r in results:
        icon    = "✓" if r.ok        else ("⚠" if r.status == "parse_error" else "✗")
        status  = r.status.upper()
        elapsed = f"{r.elapsed_s:>5.1f}"

        # Brief findings summary
        if r.raw_json is None:
            findings = r.stderr[:60] if r.stderr else "No output"
        elif isinstance(r.raw_json, list):
            if r.tool == "eslint":
                total = sum(f.get("errorCount", 0) + f.get("warningCount", 0)
                            for f in r.raw_json if isinstance(f, dict))
                findings = f"{total} ESLint messages across {len(r.raw_json)} files"
            else:
                findings = f"{len(r.raw_json)} items"
        elif isinstance(r.raw_json, dict):
            findings = f"{len(r.raw_json)} top-level keys"
        else:
            findings = str(r.raw_json)[:60]

        print(f"  {icon} {r.tool:<23} {status:<14} {elapsed}   {findings}")

    print("  " + "-" * 66)
    all_ok = sum(1 for r in results if r.ok)
    print(f"  Tools succeeded: {all_ok}/{len(results)}   Total wall time: {total_elapsed:.1f}s")
    print()
    print(f"  Raw JSON outputs saved to: {RAW_DIR}")
    print()
    print("  NEXT: Run adapters to normalise raw JSON → SARIFResult objects.")
    print("=" * 70)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    cfg       = _load_config()
    base_path = cfg.get("base_path", "").strip()
    v4_root   = str(BASE)

    if not base_path or not Path(base_path).exists():
        logger.error(
            "base_path '%s' does not exist. Set it in config/project_config.yaml.",
            base_path,
        )
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 70)
    print("  Code Audit Librarian V4 — Modernized Pipeline")
    print(f"  Source : {base_path}")
    print(f"  DB     : {cfg['db']['database']} @ {cfg['db']['host']}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print("  Phase 1: Launching Node.js tools in parallel...")
    print()

    # ── Define all tool tasks ─────────────────────────────────────────────────
    # Each entry: (label, callable, args)
    tool_tasks: list[tuple[str, Any]] = [
        ("eslint",            lambda: run_eslint(base_path, v4_root)),
        ("stylelint",         lambda: run_stylelint(base_path, v4_root)),
        ("cspell",            lambda: run_cspell(base_path, v4_root)),
        ("vue-mess-detector", lambda: run_vue_mess_detector(base_path)),
        ("dependency-cruiser",lambda: run_dependency_cruiser(base_path)),
        ("jscpd",             lambda: run_jscpd(base_path)),
    ]

    results:      list[ToolResult] = []
    future_to_label: dict[Future, str] = {}

    wall_start = time.perf_counter()

    # ── Parallel execution ────────────────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=len(tool_tasks)) as pool:
        for label, task_fn in tool_tasks:
            future = pool.submit(task_fn)
            future_to_label[future] = label

        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("[%s] Unhandled exception: %s", label, exc)
                result = ToolResult(tool=label, status="error", raw_text=str(exc))

            _save_raw(result)
            results.append(result)

    total_elapsed = round(time.perf_counter() - wall_start, 2)

    # ── Sort results back into tool_tasks order for consistent display ─────────
    order = {label: i for i, (label, _) in enumerate(tool_tasks)}
    results.sort(key=lambda r: order.get(r.tool, 99))

    _print_summary(results, total_elapsed)

    # ── Phase 2 stub (adapter normalization — coming next step) ───────────────
    logger.info(
        "Phase 1 capture complete. %d/%d tools produced JSON output. "
        "Adapter normalization (Phase 2) not yet implemented.",
        sum(1 for r in results if r.raw_json is not None),
        len(results),
    )


if __name__ == "__main__":
    main()
