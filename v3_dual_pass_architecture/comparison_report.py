"""
V3 Comparison Report Orchestrator (Corrected Architecture)

Configuration is loaded from .env in this directory.
Required .env variables:
  GROQ_API_KEY      - your Groq API key
  AUDIT_TOOL_DIR    - base folder containing task3/, task6/, task7/ subdirectories
  VUE_PROJECT_ROOT  - Vue project root folder (the one containing /src)

The script auto-discovers the 3 JSON reports from AUDIT_TOOL_DIR by
scanning all subdirectories for the known report filenames.
"""
import json
import os
from dotenv import load_dotenv
from dual_pass_analyzer import analyze_file
from confidence_calculator import calculate_confidence

# ── Load all configuration from .env ─────────────────────────────────────────
load_dotenv()

AUDIT_TOOL_DIR   = os.getenv("AUDIT_TOOL_DIR")
VUE_PROJECT_ROOT = os.getenv("VUE_PROJECT_ROOT")

# Report filenames the script looks for (no paths hardcoded)
ISSUE_REPORT_NAME       = "issue_report.json"
COMPLEXITY_REPORT_NAME  = "component_complexity.json"
ACCESSIBILITY_REPORT_NAME = "accessibility_report.json"

# ── Auto-discover report files from AUDIT_TOOL_DIR ───────────────────────────

def find_report(base_dir, filename):
    """Recursively search base_dir for a file named `filename`."""
    for root, _dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

def load_static_data():
    """Locate and load all 3 static JSON reports."""
    if not AUDIT_TOOL_DIR:
        raise ValueError("AUDIT_TOOL_DIR is not set in your .env file.")
    if not VUE_PROJECT_ROOT:
        raise ValueError("VUE_PROJECT_ROOT is not set in your .env file.")

    issue_path    = find_report(AUDIT_TOOL_DIR, ISSUE_REPORT_NAME)
    complex_path  = find_report(AUDIT_TOOL_DIR, COMPLEXITY_REPORT_NAME)
    a11y_path     = find_report(AUDIT_TOOL_DIR, ACCESSIBILITY_REPORT_NAME)

    missing = [name for name, path in [
        (ISSUE_REPORT_NAME, issue_path),
        (COMPLEXITY_REPORT_NAME, complex_path),
        (ACCESSIBILITY_REPORT_NAME, a11y_path)
    ] if path is None]

    if missing:
        raise FileNotFoundError(
            f"Could not find the following reports inside '{AUDIT_TOOL_DIR}': {missing}"
        )

    print(f"  Found: {issue_path}")
    print(f"  Found: {complex_path}")
    print(f"  Found: {a11y_path}")

    with open(issue_path, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    with open(complex_path, 'r', encoding='utf-8') as f:
        complexity = json.load(f)
    with open(a11y_path, 'r', encoding='utf-8') as f:
        accessibility = json.load(f)

    return issues, complexity, accessibility

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_complexity_for_file(complexity_data, relative_path):
    for entry in complexity_data.get("componentComplexity", []):
        if entry.get("file", "") == relative_path:
            return {
                "lines": entry.get("lines", 0),
                "methods": entry.get("methods", 0),
                "computed": entry.get("computed", 0),
                "watchers": entry.get("watchers", 0),
                "templateLines": entry.get("templateLines", 0),
                "childComponents": entry.get("childComponents", 0),
                "flags": entry.get("flags", [])
            }
    return {"lines": 0, "methods": 0, "computed": 0, "watchers": 0,
            "templateLines": 0, "childComponents": 0, "flags": []}

def get_a11y_for_file(a11y_data, relative_path):
    defects = []
    for entry in a11y_data.get("accessibility_defects", []):
        if entry.get("file_path", "") == relative_path:
            defects.append({
                "type": entry.get("defect_type", ""),
                "element": entry.get("element", ""),
                "severity": entry.get("severity", ""),
                "line_number": entry.get("line_number", 0),
                "rule": entry.get("rule", "")
            })
    return defects

# ── Main orchestrator ─────────────────────────────────────────────────────────

def generate_report():
    print("Loading static data...")
    issues_data, complexity_data, a11y_data = load_static_data()

    # Filter to 5 small files (< 350 lines) to stay within Groq's context window
    files_to_process = []
    for f_node in issues_data.get("files", []):
        lines_count = f_node.get("metrics", {}).get("lines", 9999)
        if lines_count < 350:
            files_to_process.append(f_node)
        if len(files_to_process) >= 5:
            break

    print(f"\nSelected {len(files_to_process)} files for analysis.\n")

    final_report = []

    for f_node in files_to_process:
        # Paths in the report are relative to /src (e.g. "views/Login.vue")
        rel_path = f_node["file"]
        filename = os.path.basename(rel_path)
        abs_path = os.path.join(VUE_PROJECT_ROOT, "src", rel_path.replace("/", os.sep))

        print(f"Processing {filename}...")

        # Gather static findings for this file
        static_findings = []
        for issue in f_node.get("issues", []):
            finding = {
                "type": issue.get("name", issue.get("defect_type", "")),
                "category": issue.get("category", issue.get("rule", "")),
                "severity": issue.get("severity", "MEDIUM")
            }
            if "line_number" in issue:
                finding["line_number"] = issue["line_number"]
            if "element" in issue:
                finding["element"] = issue["element"]
            static_findings.append(finding)

        # Add accessibility defects
        for defect in get_a11y_for_file(a11y_data, rel_path):
            static_findings.append({
                "type": defect["type"],
                "category": defect["rule"],
                "severity": defect["severity"],
                "line_number": defect["line_number"],
                "element": defect["element"]
            })

        complexity_metrics = get_complexity_for_file(complexity_data, rel_path)

        if not os.path.exists(abs_path):
            print(f"  -> File not found on disk: {abs_path}, skipping.")
            continue

        pass1, pass2 = analyze_file(abs_path, static_findings, complexity_metrics)
        merged = calculate_confidence(pass1, pass2)

        print(f"  -> Verified: {len(merged.get('verified_findings', []))} | "
              f"Rejected: {len(merged.get('rejected_findings', []))}\n")

        final_report.append({
            "file": filename,
            "relative_path": rel_path,
            "static_findings_fed": len(static_findings),
            "complexity_metrics": complexity_metrics,
            "verified_findings": merged.get("verified_findings", []),
            "rejected_as_false_positive": merged.get("rejected_findings", [])
        })

    output_path = os.path.join(os.path.dirname(__file__), "poc_comparison_output.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2)

    print(f"Report generated at: {output_path}")


if __name__ == "__main__":
    generate_report()