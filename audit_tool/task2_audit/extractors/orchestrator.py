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

    from extractors.vue_parser         import parse_vue_file
    from extractors.script_cleaner     import clean_script
    from extractors.complexity_checker import check_complexity
    from extractors.template_extractor import extract_template_metrics
    from extractors.api_extractor      import extract_api_calls
    from extractors.props_emits_extractor import extract_props_emits
    from checkers.flag_engine          import evaluate_flags, summarise_flags

    # Use the dynamic module name from cfg (calculated in run_audit.py)
    module = cfg.get("module", "unknown")
    confidence = cfg.get("mql", {}).get("confidence", "HIGH")

    # Default empty result
    empty = {
        "file": filepath, "module": module, "confidence": confidence,
        "extracted_metrics": {
            "script_lines": 0, "methods": 0, "computed": 0, "watchers": 0,
            "api_total": 0, "api_in_mounted": 0, "api_duplicates": [],
            "template_lines": 0, "child_components": 0, "max_nest_depth": 0,
            "payload_keys": 0, "payload_depth": 0, "payload_size_kb": 0.0,
            "prop_count": 0,
        },
        "api_calls": [], "flags_triggered": [], "flags_by_category": {},
        "flags_count": 0, "error": None,
        "props": [], "emits": []
    }

    try:
        # Step 1: Parse
        with open(filepath, "rb") as f:
            source_bytes = f.read()
        parsed     = parse_vue_file(filepath)
        raw_script = parsed.get("script_text") or ""
        script_lang = parsed.get("script_lang", "js")
        script_ts_tree = parsed.get("script_ts_tree")
        tmpl_node  = parsed.get("template_node")

        # Step 2: Clean
        clean = clean_script(raw_script)

        # Step 3: Complexity
        complexity = check_complexity(
            script_text=raw_script,
            template_node=tmpl_node,
            script_lang=script_lang,
            script_ts_tree=script_ts_tree
        )
        
        # Step 3.5: Props & Emits
        props_emits = extract_props_emits(
            script_text=raw_script,
            script_lang=script_lang,
            script_ts_tree=script_ts_tree
        )

        # Step 4: Template
        template = extract_template_metrics(tmpl_node, source_bytes)

        # Step 5: API
        api_data = extract_api_calls(clean, raw_script, filepath, config_path)

        # Step 6: Flags
        flags = evaluate_flags(
            lines             = complexity["lines"],
            methods           = complexity["methods"],
            computed          = complexity["computed"],
            watchers          = complexity["watchers"],
            api_calls         = api_data["calls"],
            duplicate_names   = api_data["methods_with_same_name"],
            template_lines    = template["template_lines"],
            child_components  = template["child_components"],
            max_nesting_depth = template["max_nesting_depth"],
            prop_count        = len(props_emits["props"]),
            payload_keys      = 0,
            payload_depth     = 0,
            payload_size_kb   = 0.0,
        )
        flag_summary = summarise_flags(flags)

        return {
            "file"      : filepath,
            "module"    : api_data.get("module") or module,
            "confidence": confidence,
            "extracted_metrics": {
                "script_lines"    : complexity["lines"],
                "methods"         : complexity["methods"],
                "computed"        : complexity["computed"],
                "watchers"        : complexity["watchers"],
                "api_total"       : api_data["total_count"],
                "api_in_mounted"  : api_data["mounted_count"],
                "api_duplicates"  : api_data["methods_with_same_name"],
                "template_lines"  : template["template_lines"],
                "child_components": template["child_components"],
                "max_nest_depth"  : template["max_nesting_depth"],
                "prop_count"      : len(props_emits["props"]),
                "payload_keys"    : 0,
                "payload_depth"   : 0,
                "payload_size_kb" : 0.0,
            },
            "api_calls"         : api_data["calls"],
            "props"             : props_emits["props"],
            "emits"             : props_emits["emits"],
            "flags_triggered"   : flags,
            "flags_by_category" : flag_summary,
            "flags_count"       : len(flags),
            "error"             : None,
        }

    except Exception as exc:
        logger.error("[orchestrator] Failed on '%s': %s", filepath, exc)
        result = dict(empty)
        result["error"] = str(exc)
        return result


def scan_all_vue_files(base_path: str, cfg: dict, config_path: str) -> list:
    """
    Find every .vue file under base_path and run the full pipeline on each.

    Args:
        base_path   (str) : Root folder to scan recursively.
        cfg         (dict): Parsed project_config.yaml.
        config_path (str) : Path to config file.

    Returns:
        list[dict]: One result dict per .vue file.
    """
    from extractors.vue_parser import get_all_vue_files

    vue_files = get_all_vue_files(base_path)
    total     = len(vue_files)
    results   = []

    logger.info("[orchestrator] Found %d .vue files under '%s'.", total, base_path)

    for idx, filepath in enumerate(vue_files, 1):
        logger.info("[orchestrator] [%d/%d] %s", idx, total,
                    Path(filepath).name)
        result = run_pipeline_on_file(filepath, cfg, config_path)
        results.append(result)

    logger.info("[orchestrator] Scan complete: %d files processed.", total)
    return results
