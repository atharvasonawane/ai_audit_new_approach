"""
Module: issue_detector.py
Description: The unified issue detection engine for Task 7. It processes data fetched via
             the DB Report Loader and calculates risk levels for all files, outputting a 
             unified JSON report. Contains ZERO direct SQL queries.
"""

import json
import logging
from pathlib import Path
from . import db_report_loader

logger = logging.getLogger(__name__)

def evaluate_risk_level(file_flags, ui_defects, accessibility_defects):
    """
    Evaluates the risk level based on the combination of architectural flags 
    and defect severities.
    """
    flag_names = set(f.get("flag_name", "") for f in file_flags)
    
    # Collect severities across UI and Accessibility, ensuring uppercase for comparison
    severities = set()
    for d in ui_defects:
        sev = d.get("severity", "").upper()
        if sev: severities.add(sev)
    for d in accessibility_defects:
        sev = d.get("severity", "").upper()
        if sev: severities.add(sev)

    # 1. CRITICAL
    if "CRITICAL" in severities or \
       "MONOLITH_COMPONENT" in flag_names or \
       "EXCESSIVE_API_USAGE" in flag_names:
        return "CRITICAL"
        
    # 2. HIGH
    if "HIGH" in severities or \
       "VERY_LARGE_COMPONENT" in flag_names or \
       "CRITICAL_COMPONENT" in flag_names:
        return "HIGH"
        
    # 3. MEDIUM
    if "MEDIUM" in severities or \
       "LARGE_COMPONENT" in flag_names or \
       "MANY_METHODS" in flag_names:
        return "MEDIUM"
        
    # 4. LOW
    if "LOW" in severities:
        return "LOW"
        
    # 5. CLEAN (fallback)
    return "CLEAN"

def generate_severity_summary(ui_defects, accessibility_defects):
    """Summarizes defect counts by severity for a single file."""
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for d in (ui_defects + accessibility_defects):
        sev = d.get("severity", "").lower()
        if sev in summary:
            summary[sev] += 1
            
    return summary

def main(cfg: dict):
    """
    Main entrypoint for the Issue Detection Engine context.
    Orchestrates the data fetch, grouping, evaluating, and writing.
    """
    logger.info("[issue_detector] Running Unified Issue Detection Engine...")
    
    # 1. Load basic file metrics
    vue_files = db_report_loader.load_component_complexity(cfg)
    if not vue_files:
        logger.warning("[issue_detector] No files found in database.")
        return

    # 2. Load all associated data
    all_api_calls = db_report_loader.load_api_calls(cfg)
    all_flags = db_report_loader.load_file_flags(cfg)
    all_ui_defects = db_report_loader.load_ui_defects(cfg)
    all_a11y_defects = db_report_loader.load_accessibility_defects(cfg)

    # Map secondary data to file_id for quick O(1) lookups
    def group_by_file_id(record_list):
        grouped = {}
        for r in record_list:
            fid = r.get("file_id")
            if fid not in grouped: grouped[fid] = []
            grouped[fid].append(r)
        return grouped

    api_by_file = group_by_file_id(all_api_calls)
    flags_by_file = group_by_file_id(all_flags)
    ui_by_file = group_by_file_id(all_ui_defects)
    a11y_by_file = group_by_file_id(all_a11y_defects)

    processed_files = []
    
    # Global tracking for summary
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAN": 0}
    total_issues = 0
    most_critical_file = None

    for f in vue_files:
        fid = f.get("id")
        fpath = f.get("file_path", "")
        
        file_api_calls = api_by_file.get(fid, [])
        file_flags = flags_by_file.get(fid, [])
        file_ui_def = ui_by_file.get(fid, [])
        file_a11y_def = a11y_by_file.get(fid, [])

        # Construct rich issue objects to prevent data loss and retain actionable metadata
        issue_list = []
        for flag in file_flags:
            issue_list.append({
                "type": "FLAG",
                "name": flag.get("flag_name", ""),
                "category": flag.get("category", "")
            })
            
        for d in file_ui_def:
            issue_list.append({
                "type": "UI_DEFECT",
                "defect_type": d.get("defect_type", ""),
                "severity": d.get("severity", ""),
                "element_type": d.get("element_type", ""),
                "snippet": d.get("trigger_text", "")
            })
            
        for d in file_a11y_def:
            issue_list.append({
                "type": "A11Y_DEFECT",
                "rule": d.get("rule", ""),
                "defect_type": d.get("defect_type", ""),
                "severity": d.get("severity", ""),
                "line_number": d.get("line_number", 0),
                "element": d.get("element", "")
            })

        total_issues += len(issue_list)

        # Risk Math
        risk = evaluate_risk_level(file_flags, file_ui_def, file_a11y_def)
        risk_counts[risk] += 1
        
        if risk == "CRITICAL" and not most_critical_file:
            most_critical_file = fpath
            
        # REMOVE BLOAT: Only include files that have at least one UI or Accessibility defect.
        # Files with only structural code-quality flags (e.g. DEEP_NESTED_TEMPLATE) but no
        # accessibility or UI issues do not require frontend developer review at this stage.
        if len(file_ui_def) == 0 and len(file_a11y_def) == 0:
            continue

        # Construct final file output object
        file_obj = {
            "file": fpath,
            "module": f.get("module", ""),
            "risk_level": risk,
            "issues": issue_list,
            "metrics": {
                "lines": f.get("script_lines", 0) + f.get("template_lines", 0),
                "methods": f.get("methods", 0),
                "computed": f.get("computed", 0),
                "watchers": f.get("watchers", 0),
                "api_calls": len(file_api_calls),
                "ui_defects": len(file_ui_def),
                "accessibility_defects": len(file_a11y_def)
            },
            "severity_summary": generate_severity_summary(file_ui_def, file_a11y_def)
        }
        processed_files.append(file_obj)

    # Sort files by risk level explicitly
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "CLEAN": 4}
    processed_files.sort(key=lambda x: risk_order.get(x["risk_level"], 5))

    # Construct overall summary block
    summary_block = {
        "summary": {
            "total_files_scanned": len(vue_files),
            "files_in_report": len(processed_files),
            "critical_files": risk_counts["CRITICAL"],
            "high_files": risk_counts["HIGH"],
            "medium_files": risk_counts["MEDIUM"],
            "low_files": risk_counts["LOW"],
            "clean_files": risk_counts["CLEAN"],
            "most_critical_file": most_critical_file or "None",
            "total_issues_found": total_issues
        },
        "files": processed_files
    }

    # Write JSON using absolute output relative to the project root
    base_dir = Path(__file__).parent.parent
    output_path = base_dir / "task7" / "issue_report.json"
    
    try:
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(summary_block, out_f, indent=2)
        logger.info("[issue_detector] Issue Report written to %s", output_path)
        
        # We'll print the console summary here so run_audit doesn't duplicate code
        summ = summary_block["summary"]
        print()
        print("  " + "━" * 32)
        print("  AUDIT COMPLETE — FINAL SUMMARY")
        print("  " + "━" * 32)
        print(f"  Total files scanned:    {summ['total_files_scanned']}")
        print(f"  Files requiring review: {summ['files_in_report']}")
        print(f"  Critical risk files:     {summ['critical_files']}")
        print(f"  High risk files:         {summ['high_files']}")
        print(f"  Medium risk files:      {summ['medium_files']}")
        print(f"  Low risk files:         {summ['low_files']}")
        print(f"  Clean files:             {summ['clean_files']}")
        print(f"  Total issues found:    {summ['total_issues_found']}")
        print(f"  Full report: task7/issue_report.json")
        print("  " + "━" * 32)
        print()
        
    except Exception as e:
        logger.error("[issue_detector] Failed to write out issue report: %s", e)
