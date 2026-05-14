"""
run_audit.py
============
Top-level entry point for the Code Audit Librarian.

Usage:
    venv\\Scripts\\python.exe run_audit.py

What it does:
    1. Reads project_config.yaml
    2. Creates / updates the MySQL schema
    3. Scans every .vue file under base_path
    4. Writes results to MySQL (vue_files, api_calls, file_flags)
    5. Saves a combined JSON report: scan_report.json
    6. Prints a summary table to console
"""

import sys
import json
import logging
import time
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ── Setup ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
TASK2_BASE = BASE / "task2_audit"
CONFIG_PATH = str(BASE / "config" / "project_config.yaml")

# Ensure the project root is on sys.path so the SQLite db package resolves first
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Insert task2_audit into sys.path so inner imports (extractors) resolve
if str(TASK2_BASE) in sys.path:
    sys.path.remove(str(TASK2_BASE))
sys.path.insert(1, str(TASK2_BASE))

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)

file_handler = logging.FileHandler(str(BASE.parent / "scan.log"), encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logging.getLogger().addHandler(file_handler)

# Silence noisy sub-loggers during scan
for noisy in (
    "extractors.vue_parser",
    "extractors.script_cleaner",
    "extractors.api_extractor",
    "extractors.complexity_checker",
    "extractors.template_extractor",
):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("run_audit")

# ── Load config ───────────────────────────────────────────────────────────────
cfg = yaml.safe_load(open(CONFIG_PATH, encoding="utf-8"))

if "project_name" not in cfg:
    logger.error(
        "Error: 'project_name' key must exist at the root level of project_config.yaml"
    )
    sys.exit(1)

project_name = cfg["project_name"]
# Dynamically set the module name. Priority:
# 1. Explicit 'module' field in config (if set and non-empty)
# 2. 'project_name' field from config
# 3. Heuristic: parent folder name of base_path
if not cfg.get("module"):
    if cfg.get("project_name"):
        cfg["module"] = cfg["project_name"]
    else:
        base_path_str = cfg.get("base_path", "").replace("\\", "/").rstrip("/")
        if base_path_str:
            # Use the leaf folder name as module identifier
            cfg["module"] = Path(base_path_str).name
        else:
            cfg["module"] = "unknown"

# Load environment variables and override database credentials safely
load_dotenv()
if "db" not in cfg:
    cfg["db"] = {}
cfg["db"]["host"] = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
cfg["db"]["port"] = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
cfg["db"]["user"] = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
cfg["db"]["database"] = os.getenv(
    "MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db")
)

BASE_PATH = cfg.get("base_path", "")

if not Path(BASE_PATH).exists():
    logger.error("base_path '%s' does not exist. Check project_config.yaml.", BASE_PATH)
    sys.exit(1)

# ── Imports ───────────────────────────────────────────────────────────────────
from extractors.orchestrator import scan_all_vue_files
from db.db_init import init_db
from db.db_writer import get_all_file_hashes, write_eslint_results, write_scan_result
from extractors.eslint_extractor import run_eslint_scan, parse_eslint_results


# ── Main ──────────────────────────────────────────────────────────────────────
def _run_scout_phase():
    logger.info("")
    logger.info("=" * 65)
    sqlite_path = Path(cfg.get("db", {}).get("path", PROJECT_ROOT / "audit_history.db"))

    logger.info("  Code Audit Librarian — Full Project Scan")
    logger.info(f"  Source : {BASE_PATH}")
    logger.info(f"  SQLite : {sqlite_path}")
    logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 65)

    # 1. Setup SQLite schema
    logger.info("Setting up SQLite schema...")
    init_db(sqlite_path)

    # 2. Load known file hashes from database into memory for fast lookup
    logger.info("Loading known file hashes from database into memory...")
    known_hashes = get_all_file_hashes(project_name, sqlite_path)
    logger.info(
        "Loaded %d known file hashes into memory for incremental auditing",
        len(known_hashes),
    )

    # 3. Scan all files (with incremental auditing using in-memory hash lookup)
    start = time.time()
    logger.info("Starting incremental scan...")
    results, dirty_files = scan_all_vue_files(BASE_PATH, cfg, CONFIG_PATH, known_hashes)
    elapsed = time.time() - start
    logger.info(
        "Incremental scan complete in %.1fs — %d files found, %d processed.",
        elapsed,
        len(results),
        len(dirty_files),
    )
    logger.info(f"[DEBUG] Total files marked as dirty: {len(dirty_files)}")

    # 4. Write to DB (only dirty files)
    logger.info("Writing dirty file results to SQLite...")
    errors = 0
    written_count = 0
    for i, result in enumerate(results, 1):
        # Skip files that were unchanged (already in DB)
        if result.get("skipped"):
            continue

        try:
            write_scan_result(project_name, cfg, result, sqlite_path)
            written_count += 1
        except Exception as e:
            logger.error("DB write failed for %s: %s", result.get("file", "?"), e)
            errors += 1
        if written_count > 0 and written_count % 20 == 0:
            logger.info("  Written %d dirty files...", written_count)

    logger.info(
        "DB write complete: %d dirty files written, %d errors", written_count, errors
    )

    # 5. Run ESLint scan and save results to DB (targeted for dirty files only)
    if dirty_files:
        logger.info(
            "Running targeted ESLint scan on %d dirty files...", len(dirty_files)
        )
        try:
            scan_ok = run_eslint_scan(BASE_PATH, dirty_files)
            if scan_ok:
                eslint_results = parse_eslint_results()
                if eslint_results:
                    eslint_counts = write_eslint_results(
                        project_name, cfg, eslint_results, sqlite_path
                    )
                    logger.info(
                        "  Written %d ESLint flags to file_flags, %d to accessibility_defects",
                        eslint_counts["file_flags"],
                        eslint_counts["accessibility_defects"],
                    )
                    logger.info(
                        f"ESLint found {eslint_counts['accessibility_defects']} accessibility issues"
                    )
                else:
                    logger.info("  No ESLint issues found in dirty files")
            else:
                logger.warning("  ESLint scan did not generate a report")
        except Exception as e:
            logger.error("  ESLint scan failed: %s", e)
    else:
        logger.info("Skipping ESLint scan - no dirty files found (all files unchanged)")

    # 6. Summary table
    processed_results = [r for r in results if not r.get("skipped")]
    skipped_results = [r for r in results if r.get("skipped")]

    total_flags = sum(r["flags_count"] for r in processed_results)
    ok = [r for r in processed_results if not r.get("error")]
    flagged = [r for r in ok if r["flags_count"] > 0]
    clean = [r for r in ok if r["flags_count"] == 0]

    top10 = sorted(ok, key=lambda r: r["flags_count"], reverse=True)[:10]

    logger.info("")
    logger.info("=" * 65)
    logger.info("  INCREMENTAL SCAN SUMMARY")
    logger.info("=" * 65)
    logger.info(f"  Total files found   : {len(results)}")
    logger.info(f"  Files processed     : {len(processed_results)}")
    logger.info(f"  Files skipped       : {len(skipped_results)}")
    logger.info(f"  Errors              : {errors}")
    logger.info(f"  Clean files         : {len(clean)}")
    logger.info(f"  Flagged files       : {len(flagged)}")
    logger.info(f"  Total flags         : {total_flags}")
    logger.info(f"  Elapsed time        : {elapsed:.1f}s")
    logger.info("")
    logger.info("  TOP 10 MOST FLAGGED FILES:")
    logger.info(f"  {'File':<45} {'Flags':>5}  Triggered")
    logger.info("  " + "-" * 62)
    for r in top10:
        fname = Path(r["file"]).name
        flag_names = [
            f["flag"] if isinstance(f, dict) else f for f in r["flags_triggered"]
        ]
        logger.info(
            f"  {fname:<45} {r['flags_count']:>5}  {', '.join(flag_names[:3])}{'...' if len(flag_names) > 3 else ''}"
        )
    logger.info("")
    logger.info(f"  DB   : sqlite ({len(processed_results)} new/updated rows)")
    logger.info("Scout Phase Complete.")


def _run_ai_phase(resume: bool):
    import builtins
    logger.info("Starting AI Agent Phase...")
    
    # Monkeypatch input() to automatically pass the resume flag
    original_input = builtins.input
    if resume:
        def mock_input(prompt=""):
            logger.info(f"Auto-answering 'y' to AI agent prompt: {prompt}")
            return "y"
        builtins.input = mock_input
    else:
        def mock_input(prompt=""):
            logger.info(f"Auto-answering 'n' to AI agent prompt: {prompt}")
            return "n"
        builtins.input = mock_input

    try:
        from mcp_agent.agent import run_full_codebase_audit
        run_full_codebase_audit()
    except ImportError as e:
        logger.error(f"Could not import AI agent: {e}")
    except Exception as e:
        logger.error(f"AI Agent failed: {e}")
    finally:
        builtins.input = original_input
        logger.info("AI Agent Phase Complete.")


def _run_report_phase():
    import subprocess
    import sys
    try:
        import psutil
    except ImportError:
        psutil = None

    logger.info("Starting Report Phase (Frontend & Backend)...")
    
    # Resolve the base directory dynamically (project root is one level up from audit_tool)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    backend_cmd = [sys.executable, os.path.join(base_dir, "report", "api_server.py")]
    frontend_cmd = "npm run dev"
    frontend_cwd = os.path.join(base_dir, "report", "frontend")
    
    logger.info(f"Launching Backend Server: {' '.join(backend_cmd)}")
    backend_proc = subprocess.Popen(backend_cmd)
    
    logger.info(f"Launching Frontend Server: {frontend_cmd} (cwd: {frontend_cwd})")
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_cwd, shell=True)
    
    try:
        logger.info("Servers are running. Press Ctrl+C to shut down.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down servers cleanly...")
    finally:
        logger.info("Killing backend process...")
        if psutil:
            try:
                parent = psutil.Process(backend_proc.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
            except psutil.NoSuchProcess:
                pass
        else:
            backend_proc.terminate()
            
        logger.info("Killing frontend process tree...")
        if psutil:
            try:
                parent = psutil.Process(frontend_proc.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
            except psutil.NoSuchProcess:
                pass
        else:
            # Fallback for Windows shell=True process tree
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            frontend_proc.terminate()
            
        logger.info("Shutdown complete.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Code Audit Librarian Orchestrator")
    parser.add_argument("--scout-only", action="store_true", help="Runs only Phase 1 (deterministic extractors) and exits.")
    parser.add_argument("--ai-only", action="store_true", help="Runs the AI phase and exits.")
    parser.add_argument("--resume", action="store_true", help="Resumes a previously interrupted run (for AI phase).")
    parser.add_argument("--report-only", action="store_true", help="Boots the frontend and backend servers simultaneously and keeps them alive.")
    
    args = parser.parse_args()

    run_scout = False
    run_ai = False
    run_report = False

    if args.scout_only:
        run_scout = True
    elif args.ai_only:
        run_ai = True
    elif args.report_only:
        run_report = True
    else:
        # Default: runs sequentially
        run_scout = True
        run_ai = True
        run_report = True

    if run_scout:
        _run_scout_phase()
    
    if run_ai:
        _run_ai_phase(resume=args.resume)
    
    if run_report:
        _run_report_phase()


if __name__ == "__main__":
    main()
