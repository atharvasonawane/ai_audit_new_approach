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
BASE        = Path(__file__).parent
TASK2_BASE  = BASE / "task2_audit"
CONFIG_PATH = str(TASK2_BASE / "config" / "project_config.yaml")

# Insert task2_audit into sys.path so inner imports (extractors, db) resolve perfectly
sys.path.insert(0, str(TASK2_BASE))

import yaml

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s %(name)s -- %(message)s",
    datefmt = "%H:%M:%S",
)
# Silence noisy sub-loggers during scan
for noisy in ("extractors.vue_parser", "extractors.script_cleaner",
              "extractors.mql_extractor", "extractors.complexity_checker",
              "extractors.template_extractor"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("run_audit")

# ── Load config ───────────────────────────────────────────────────────────────
cfg      = yaml.safe_load(open(CONFIG_PATH, encoding="utf-8"))

# Load environment variables and override database credentials safely
load_dotenv()
if "db" not in cfg:
    cfg["db"] = {}
cfg["db"]["host"]     = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
cfg["db"]["port"]     = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
cfg["db"]["user"]     = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
cfg["db"]["database"] = os.getenv("MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db"))

BASE_PATH = cfg.get("base_path", "")

if not Path(BASE_PATH).exists():
    logger.error("base_path '%s' does not exist. Check project_config.yaml.", BASE_PATH)
    sys.exit(1)

# ── Imports ───────────────────────────────────────────────────────────────────
from extractors.orchestrator import scan_all_vue_files
from db.db_writer            import setup_schema, write_file_result, export_db_to_json

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 65)
    print("  Code Audit Librarian — Full Project Scan")
    print(f"  Source : {BASE_PATH}")
    print(f"  DB     : {cfg['db']['database']} @ {cfg['db']['host']}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    # 1. Setup DB schema
    logger.info("Setting up database schema...")
    setup_schema(cfg)

    # 2. Scan all files
    start = time.time()
    logger.info("Starting scan...")
    results = scan_all_vue_files(BASE_PATH, cfg, CONFIG_PATH)
    elapsed = time.time() - start
    logger.info("Scan complete in %.1fs — %d files processed.", elapsed, len(results))

    # 3. Write to DB
    logger.info("Writing results to MySQL...")
    errors = 0
    for i, result in enumerate(results, 1):
        try:
            write_file_result(cfg, result)
        except Exception as e:
            logger.error("DB write failed for %s: %s", result.get("file","?"), e)
            errors += 1
        if i % 20 == 0:
            logger.info("  Written %d / %d files...", i, len(results))

    # 4. Save combined JSON (Removed: Relying entirely on the DB export)

    # 5. Summary table
    total_flags = sum(r["flags_count"] for r in results)
    ok          = [r for r in results if not r.get("error")]
    flagged     = [r for r in ok if r["flags_count"] > 0]
    clean       = [r for r in ok if r["flags_count"] == 0]

    # Top 10 most flagged files
    top10 = sorted(ok, key=lambda r: r["flags_count"], reverse=True)[:10]

    print()
    print("=" * 65)
    print("  SCAN SUMMARY")
    print("=" * 65)
    print(f"  Files scanned  : {len(results)}")
    print(f"  Errors         : {errors}")
    print(f"  Clean files    : {len(clean)}")
    print(f"  Flagged files  : {len(flagged)}")
    print(f"  Total flags    : {total_flags}")
    print(f"  Elapsed time   : {elapsed:.1f}s")
    print()
    print("  TOP 10 MOST FLAGGED FILES:")
    print(f"  {'File':<45} {'Flags':>5}  Triggered")
    print("  " + "-" * 62)
    for r in top10:
        fname = Path(r["file"]).name
        print(f"  {fname:<45} {r['flags_count']:>5}  {', '.join(r['flags_triggered'][:3])}{'...' if len(r['flags_triggered'])>3 else ''}")
    print()
    print(f"  DB   : {cfg['db']['database']}.vue_files ({len(results)} rows)")
    
    # 6. Export Database to JSON
    db_json_path = BASE / "task2_db_export.json"
    logger.info("Exporting native database tables to %s...", db_json_path)
    export_db_to_json(cfg, str(db_json_path))
    print(f"  DB Export : {db_json_path}")
    
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
