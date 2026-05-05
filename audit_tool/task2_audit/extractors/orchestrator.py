"""
extractors/orchestrator.py
==========================
Loops over all .vue files under the configured base_path and runs the
full analysis pipeline on each one.  Returns a list of result dicts
ready for db_writer and JSON export.

Pipeline per file:
    vue_parser -> script_cleaner -> complexity_checker
               -> template_extractor -> mql_extractor -> flag_engine
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_pipeline_on_file(filepath: str, cfg: dict, config_path: str) -> dict:
    """
    Run the full analysis pipeline on a single .vue file.

    Args:
        filepath    (str) : Absolute path to the .vue file.
        cfg         (dict): Parsed project_config.yaml.
        config_path (str) : Path to config file (needed by mql_extractor).

    Returns:
        dict: Full result including extracted_metrics, api_calls, flags_triggered.
    """
    import sys
    from pathlib import Path as _Path

    # Ensure audit_tool is importable
    base = _Path(config_path).parent.parent
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    from extractors.vue_parser import parse_vue_file
    from extractors.script_cleaner import clean_script
    from extractors.complexity_checker import check_complexity
    from extractors.template_extractor import extract_template_metrics
    from extractors.api_extractor import (
        extract_api_calls,
        count_payload_keys,
        calculate_payload_depth,
        calculate_payload_size_kb,
    )
    from checkers.flag_engine import evaluate_flags, summarise_flags
    from db.db_writer import calculate_file_hash, check_file_hash_exists
    from extractors.path_utils import normalize_path

    # Use the dynamic module name from cfg (calculated in run_audit.py)
    module = cfg.get("module", "unknown")
    confidence = cfg.get("mql", {}).get("confidence", "HIGH")

    # Calculate file hash for incremental auditing
    file_hash = calculate_file_hash(filepath)
    
    # Normalize filepath for database comparison
    base_path = cfg.get("base_path", "")
    normalized_filepath = normalize_path(filepath, base_path) if base_path else filepath.replace("\\", "/")
    
    # Check if file has unchanged content (skip mechanism)
    if check_file_hash_exists(cfg, normalized_filepath, file_hash):
        logger.info("Skipping %s (Unchanged)", Path(filepath).name)
        return {
            "file": filepath,
            "module": module,
            "confidence": confidence,
            "extracted_metrics": {},
            "api_calls": [],
            "flags_triggered": [],
            "flags_by_category": {},
            "flags_count": 0,
            "error": None,
            "skipped": True,
            "file_hash": file_hash,
        }

    # Default empty result
    empty = {
        "file": filepath,
        "module": module,
        "confidence": confidence,
        "extracted_metrics": {
            "script_lines": 0,
            "methods": 0,
            "computed": 0,
            "watchers": 0,
            "api_total": 0,
            "api_in_mounted": 0,
            "api_duplicates": [],
            "template_lines": 0,
            "child_components": 0,
            "max_nest_depth": 0,
            "payload_keys": 0,
            "payload_depth": 0,
            "payload_size_kb": 0.0,
        },
        "api_calls": [],
        "flags_triggered": [],
        "flags_by_category": {},
        "flags_count": 0,
        "error": None,
        "skipped": False,
        "file_hash": file_hash,
    }

    try:
        # Step 1: Parse
        with open(filepath, "rb") as f:
            source_bytes = f.read()
        parsed = parse_vue_file(filepath)
        raw_script = parsed.get("script_text") or ""
        tmpl_node = parsed.get("template_node")

        # Parse Validation Logging
        raw_lines = len(source_bytes.splitlines())
        if raw_lines > 30 and not raw_script.strip() and tmpl_node is None:
            logger.warning(
                "File %s has %d lines but parsed as empty", str(filepath), raw_lines
            )

        # Step 2: Clean
        clean = clean_script(raw_script)

        # Step 3: Complexity
        complexity = check_complexity(
            script_text=raw_script,
            is_script_setup=parsed.get("is_script_setup", False),
            script_lang=parsed.get("script_lang")
        )

        # Step 4: Template
        template = extract_template_metrics(tmpl_node, source_bytes, raw_script)

        # Step 5: API
        script_start_line = parsed.get("script_start_line") or 1
        api_data = extract_api_calls(clean, raw_script, filepath, config_path, script_start_line)

        # Calculate payload metrics
        total_payload_keys = count_payload_keys(clean)
        max_payload_depth = calculate_payload_depth(clean)
        total_payload_size = calculate_payload_size_kb(clean)

        # Step 6: Flags
        flags = evaluate_flags(
            lines=complexity["lines"],
            methods=complexity["methods"],
            computed=complexity["computed"],
            watchers=complexity["watchers"],
            api_calls=api_data["calls"],
            duplicate_names=api_data["methods_with_same_name"],
            template_lines=template["template_lines"],
            child_components=template["child_components"],
            max_nesting_depth=template["max_nesting_depth"],
            payload_keys=total_payload_keys,
            payload_depth=max_payload_depth,
            payload_size_kb=total_payload_size,
        )
        flag_summary = summarise_flags(flags)

        return {
            "file": filepath,
            "module": api_data.get("module") or module,
            "confidence": confidence,
            "extracted_metrics": {
                "script_lines": complexity["lines"],
                "methods": complexity["methods"],
                "computed": complexity["computed"],
                "watchers": complexity["watchers"],
                "api_total": api_data["total_count"],
                "api_in_mounted": api_data["mounted_count"],
                "api_duplicates": api_data["methods_with_same_name"],
                "template_lines": template["template_lines"],
                "child_components": template["child_components"],
                "max_nest_depth": template["max_nesting_depth"],
                "payload_keys": total_payload_keys,
                "payload_depth": max_payload_depth,
                "payload_size_kb": total_payload_size,
            },
            "api_calls": api_data["calls"],
            "flags_triggered": flags,
            "flags_by_category": flag_summary,
            "flags_count": len(flags),
            "error": None,
            "skipped": False,
            "file_hash": file_hash,
        }

    except Exception as exc:
        logger.error("[orchestrator] Failed on '%s': %s", filepath, exc)
        result = dict(empty)
        result["error"] = str(exc)
        return result


def scan_all_vue_files(base_path: str, cfg: dict, config_path: str) -> tuple[list, list]:
    """
    Find every .vue file under base_path and run the full pipeline on each.
    Implements incremental auditing by skipping unchanged files.

    Args:
        base_path   (str) : Root folder to scan recursively.
        cfg         (dict): Parsed project_config.yaml.
        config_path (str) : Path to config file.

    Returns:
        tuple: (results, dirty_files) where:
            - results: list[dict] - One result dict per .vue file (including skipped)
            - dirty_files: list[str] - List of file paths that were actually processed
    """
    from extractors.vue_parser import get_all_vue_files

    vue_files = get_all_vue_files(base_path)
    total = len(vue_files)
    results = []
    dirty_files = []

    logger.info("[orchestrator] Found %d .vue files under '%s'.", total, base_path)
    logger.info("[orchestrator] Starting incremental audit with SHA-256 hashing...")

    processed_count = 0
    skipped_count = 0

    for idx, filepath in enumerate(vue_files, 1):
        result = run_pipeline_on_file(filepath, cfg, config_path)
        results.append(result)
        
        if result.get("skipped"):
            skipped_count += 1
        else:
            processed_count += 1
            dirty_files.append(filepath)
            logger.info("[orchestrator] [%d/%d] Processing %s", idx, total, Path(filepath).name)

    logger.info("[orchestrator] Incremental scan complete:")
    logger.info("[orchestrator]   - Total files found: %d", total)
    logger.info("[orchestrator]   - Files processed (dirty): %d", processed_count)
    logger.info("[orchestrator]   - Files skipped (unchanged): %d", skipped_count)
    
    return results, dirty_files
