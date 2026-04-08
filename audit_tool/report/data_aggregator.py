"""
Data Aggregator v2 — reads ALL task JSONs (task3–task7) directly.
Builds dedicated defect lists for each category instead of a single unified list.
"""
import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ===== JSON Paths =====
TASK3_JSON = os.path.join(BASE_DIR, "task3", "component_complexity.json")
TASK4_JSON = os.path.join(BASE_DIR, "task4", "ui_extraction.json")
TASK5_JSON = os.path.join(BASE_DIR, "task5", "ui_consistency_report.json")
TASK6_JSON = os.path.join(BASE_DIR, "task6", "accessibility_report.json")
TASK7_JSON = os.path.join(BASE_DIR, "task7", "issue_report.json")


def _safe_load(path):
    """Load a JSON file safely, returning None on failure."""
    if not os.path.exists(path):
        print(f"  [WARN] File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def _basename(filepath):
    """Extract the Vue file basename from a path."""
    return os.path.basename(filepath) if filepath else "unknown"


# =====================================================================
# TASK 3: Component Complexity — extract flags as defects
# =====================================================================
def load_complexity_data():
    """
    Returns:
        files: [{file, basename, lines, methods, computed, watchers,
                 templateLines, childComponents, flags: [{name, category, severity}]}]
        flags_flat: [{file, basename, name, category, severity}]  — flattened for defect section
    """
    data = _safe_load(TASK3_JSON)
    if not data:
        return [], []

    entries = data.get("componentComplexity", [])
    files = []
    flags_flat = []

    # Define severity mapping for known flags
    severity_map = {
        "HEAVY_COMPONENT": "HIGH",
        "VERY_LONG_COMPONENT": "HIGH",
        "DEEP_NESTED_TEMPLATE": "MEDIUM",
        "COMPLEX_TEMPLATE": "MEDIUM",
        "VERY_HIGH_API_USAGE": "HIGH",
        "HIGH_API_USAGE": "MEDIUM",
        "DEPENDENT_API_CALLS": "MEDIUM",
        "MANY_CHILDREN": "MEDIUM",
        "MANY_METHODS": "MEDIUM",
        "MANY_COMPUTED": "LOW",
        "MANY_WATCHERS": "LOW",
    }

    for entry in entries:
        filepath = entry.get("file", "")
        bname = _basename(filepath)
        flags = entry.get("flags", [])

        enriched_flags = []
        for flag_name in flags:
            flag_obj = {
                "name": flag_name,
                "category": "complexity",
                "severity": severity_map.get(flag_name, "LOW"),
            }
            enriched_flags.append(flag_obj)
            flags_flat.append({
                "file": filepath,
                "basename": bname,
                **flag_obj,
            })

        files.append({
            "file": filepath,
            "basename": bname,
            "lines": entry.get("lines", 0),
            "methods": entry.get("methods", 0),
            "computed": entry.get("computed", 0),
            "watchers": entry.get("watchers", 0),
            "templateLines": entry.get("templateLines", 0),
            "childComponents": entry.get("childComponents", 0),
            "flags": enriched_flags,
        })

    return files, flags_flat


# =====================================================================
# TASK 4: UI Extraction — extract raw data (no defects, but useful context)
# =====================================================================
def load_ui_extraction():
    """
    Returns: [{file, basename, uses_i18n, buttons: [...], headers: [...], visibleTexts: [...]}]
    """
    data = _safe_load(TASK4_JSON)
    if not data:
        return []

    entries = data.get("uiExtraction", [])
    result = []
    for entry in entries:
        result.append({
            "file": entry.get("file", ""),
            "basename": _basename(entry.get("file", "")),
            "uses_i18n": entry.get("uses_i18n", False),
            "buttons": entry.get("buttons", []),
            "headers": entry.get("headers", []),
            "visibleTexts": entry.get("visibleTexts", []),
        })
    return result


# =====================================================================
# TASK 5: UI Consistency — SPELLING, CSS, PLACEHOLDER defects
# =====================================================================
def load_ui_consistency():
    """
    Returns:
        spelling_defects: [{file, basename, defect_type, severity, element_type, trigger_text, expected_text}]
        css_defects: [{file, basename, defect_type, severity, element_type, trigger_text, expected_text}]
        placeholder_defects: [{file, basename, defect_type, severity, element_type, trigger_text, expected_text}]
        consistency_scores: [{file, basename, score, total_elements, defects_count}]
    """
    data = _safe_load(TASK5_JSON)
    if not data:
        return [], [], [], []

    entries = data.get("uiConsistency", [])
    spelling = []
    css = []
    placeholder = []
    scores = []

    for entry in entries:
        filepath = entry.get("file", "")
        bname = _basename(filepath)
        score = entry.get("consistency_score")

        scores.append({
            "file": filepath,
            "basename": bname,
            "score": score,
            "total_elements": entry.get("total_ui_elements", 0),
            "defects_count": entry.get("defects_count", 0),
        })

        for defect in entry.get("defects", []):
            defect_entry = {
                "file": filepath,
                "basename": bname,
                "defect_type": defect.get("defect_type", ""),
                "severity": defect.get("severity", "LOW"),
                "element_type": defect.get("element_type", ""),
                "trigger_text": defect.get("trigger_text", ""),
                "expected_text": defect.get("expected_text", ""),
            }

            dt = defect.get("defect_type", "")
            if dt == "SPELLING":
                spelling.append(defect_entry)
            elif dt == "INCONSISTENT_CSS":
                css.append(defect_entry)
            elif dt == "PLACEHOLDER_TEXT_IN_PRODUCTION":
                placeholder.append(defect_entry)

    return spelling, css, placeholder, scores


# =====================================================================
# TASK 6: Accessibility Defects
# =====================================================================
def load_accessibility():
    """
    Returns: [{file, basename, module, rule, defect_type, element, severity, line_number}]
    """
    data = _safe_load(TASK6_JSON)
    if not data:
        return []

    entries = data.get("accessibility_defects", [])
    result = []
    for entry in entries:
        filepath = entry.get("file_path", "")
        result.append({
            "file": filepath,
            "basename": _basename(filepath),
            "module": entry.get("module", ""),
            "rule": entry.get("rule", ""),
            "defect_type": entry.get("defect_type", ""),
            "element": entry.get("element", ""),
            "severity": entry.get("severity", "LOW"),
            "line_number": entry.get("line_number", ""),
        })
    return result


# =====================================================================
# TASK 7: Issue Report — unified summary + risk assignments
# =====================================================================
def load_issue_report():
    """
    Returns:
        summary: {total_files_scanned, files_in_report, critical_files, ...}
        files: [{file, basename, module, risk_level, issues, metrics, severity_summary}]
    """
    data = _safe_load(TASK7_JSON)
    if not data:
        return {}, []

    summary = data.get("summary", {})
    raw_files = data.get("files", [])
    files = []

    for entry in raw_files:
        filepath = entry.get("file", "")
        files.append({
            "file": filepath,
            "basename": _basename(filepath),
            "module": entry.get("module", ""),
            "risk_level": entry.get("risk_level", "LOW"),
            "issues": entry.get("issues", []),
            "metrics": entry.get("metrics", {}),
            "severity_summary": entry.get("severity_summary", {}),
        })

    return summary, files


# =====================================================================
# MASTER LOADER — loads everything into a single structured dict
# =====================================================================
def load_all_data():
    """
    Load all task JSONs and return a comprehensive data structure.

    Returns: {
        summary: {...}                  — from Task 7
        files: [...]                    — from Task 7 (risk-level file table)
        complexity_files: [...]         — from Task 3
        complexity_flags: [...]         — flattened flags for complexity section
        ui_extraction: [...]            — from Task 4 (context only)
        spelling_defects: [...]         — from Task 5
        css_defects: [...]              — from Task 5
        placeholder_defects: [...]      — from Task 5
        consistency_scores: [...]       — from Task 5
        a11y_defects: [...]             — from Task 6
        category_counts: {flags, spelling, css, placeholder, a11y}
    }
    """
    print("  Loading Task 3 (component_complexity.json)...")
    complexity_files, complexity_flags = load_complexity_data()
    print(f"    → {len(complexity_files)} files, {len(complexity_flags)} flags")

    print("  Loading Task 4 (ui_extraction.json)...")
    ui_extraction = load_ui_extraction()
    print(f"    → {len(ui_extraction)} files")

    print("  Loading Task 5 (ui_consistency_report.json)...")
    spelling, css, placeholder, consistency_scores = load_ui_consistency()
    print(f"    → {len(spelling)} spelling, {len(css)} CSS, {len(placeholder)} placeholder defects")

    print("  Loading Task 6 (accessibility_report.json)...")
    a11y = load_accessibility()
    print(f"    → {len(a11y)} accessibility defects")

    print("  Loading Task 7 (issue_report.json)...")
    summary, files = load_issue_report()
    print(f"    → {len(files)} files with issues, summary loaded")

    # Build category counts
    category_counts = {
        "flags": len(complexity_flags),
        "spelling": len(spelling),
        "css": len(css),
        "placeholder": len(placeholder),
        "a11y": len(a11y),
        "total": len(complexity_flags) + len(spelling) + len(css) + len(placeholder) + len(a11y),
    }

    return {
        "summary": summary,
        "files": files,
        "complexity_files": complexity_files,
        "complexity_flags": complexity_flags,
        "ui_extraction": ui_extraction,
        "spelling_defects": spelling,
        "css_defects": css,
        "placeholder_defects": placeholder,
        "consistency_scores": consistency_scores,
        "a11y_defects": a11y,
        "category_counts": category_counts,
    }
