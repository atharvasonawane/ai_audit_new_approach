"""
eslint_adapter.py

Phase 3 - Step 5
Executes ESLint via subprocess from the audit_tool_v4 folder.
Validates the JSON output concurrently using RuleViolationModel.
Forwards cleanly-mapped results to db_loader.py.
"""

import os
import json
import logging
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Insert paths to import dependencies
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "audit_tool"))
sys.path.insert(0, str(PROJECT_ROOT / "audit_tool_v4"))

from schema_models import (
    RuleViolationModel,
    SARIFResult,
    SARIFReport,
    Category,
    Severity,
    ESLINT_SEVERITY_MAP,
    infer_category
)
from db import db_loader

logger = logging.getLogger(__name__)

V4_DIR = PROJECT_ROOT / "audit_tool_v4"


def run_eslint(base_path: str, cfg: dict) -> int:
    """
    Run ESLint, validates output using ThreadPoolExecutor, and ingest to DB.
    """
    cmd = [
        "npx", "eslint", base_path,
        "--ext", ".vue,.js,.ts",
        "--format", "json",
        "--no-eslintrc",
        "--config", str(V4_DIR / ".eslintrc.js")
    ]
    
    logger.info("Running ESLint in ThreadPoolExecutor from: %s", V4_DIR)
    
    # Run the subprocess within ThreadPoolExecutor as per instructions
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            subprocess.run,
            cmd,
            cwd=str(V4_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True if os.name == 'nt' else False
        )
        proc = future.result()

    if not proc.stdout.strip():
        logger.warning("ESLint produced no standard output.")
        return 0

    try:
        raw_json = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse ESLint JSON output: %s", exc)
        return 0

    results = parse_eslint_results(raw_json, base_path)
    
    report = SARIFReport(
        project=cfg.get("project_name", "Unknown Project"),
        base_path=base_path,
        results=results
    )
    
    # Ingest directly to db_loader
    scan_run_id = db_loader.ingest_report(cfg, report)
    logger.info("Successfully ingested ESLint findings. scan_run_id=%d", scan_run_id)
    return scan_run_id


def parse_file_result(file_entry: dict, base_path: str) -> list[SARIFResult]:
    results = []
    try:
        # Validate using the newly created Pydantic model
        validated = RuleViolationModel.model_validate(file_entry)
        
        try:
            rel_path = str(Path(validated.filePath).relative_to(Path(base_path))).replace("\\", "/")
        except ValueError:
            rel_path = Path(validated.filePath).name
        
        for msg in validated.messages:
            if msg.severity == 0:
                continue

            rule_id = msg.ruleId or "eslint:parse-error"
            severity = ESLINT_SEVERITY_MAP.get(msg.severity, Severity.WARNING)
            category = infer_category(rule_id, "eslint")
            
            snippet = None
            if msg.nodeText:
                snippet = msg.nodeText[:200]

            results.append(SARIFResult(
                tool_name="eslint",
                rule_id=rule_id,
                severity=severity,
                category=category,
                file_path=rel_path,
                line=msg.line or 1,
                column=msg.column or 0,
                message=msg.message,
                snippet=snippet
            ))
            
    except Exception as exc:
        logger.debug("Skipping file entry due to validation error: %s", exc)
        
    return results


def parse_eslint_results(raw_json: list, base_path: str) -> list[SARIFResult]:
    """Parse raw ESLint JSON entries concurrently."""
    all_results = []
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(parse_file_result, entry, base_path) for entry in raw_json]
        for f in futures:
            all_results.extend(f.result())
            
    logger.info("ESLint adapter successfully validated %d findings.", len(all_results))
    return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import yaml
    cfg_path = PROJECT_ROOT / "config" / "project_config.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {"project_name": "Test Project"}
    
    bp = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT)
    run_eslint(bp, config)
