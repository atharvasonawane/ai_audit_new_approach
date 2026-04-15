"""
V3 Comparison Report Orchestrator (Corrected Architecture)
Loads all 3 static data sources, feeds them into the dual-pass analyzer,
and outputs the final comparison report.
"""
import json
import os
from dual_pass_analyzer import analyze_file
from confidence_calculator import calculate_confidence

# Paths to existing static data
ISSUE_REPORT = r"c:\Users\Atharvaso\Desktop\final_approach\audit_tool\task7\issue_report.json"
COMPLEXITY_REPORT = r"c:\Users\Atharvaso\Desktop\final_approach\audit_tool\task3\component_complexity.json"
ACCESSIBILITY_REPORT = r"c:\Users\Atharvaso\Desktop\final_approach\audit_tool\task6\accessibility_report.json"

# Base path for resolving relative file paths from complexity report
VUE_PROJECT_ROOT = r"C:\Users\Atharvaso\Desktop\StudentManagement\StudentManagement\client\app"

def load_static_data():
    """Load all 3 static JSON reports."""
    with open(ISSUE_REPORT, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    with open(COMPLEXITY_REPORT, 'r', encoding='utf-8') as f:
        complexity = json.load(f)
    with open(ACCESSIBILITY_REPORT, 'r', encoding='utf-8') as f:
        accessibility = json.load(f)
    return issues, complexity, accessibility

def get_complexity_for_file(complexity_data, relative_path):
    """Find the complexity metrics for a given file."""
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
    return {"lines": 0, "methods": 0, "computed": 0, "watchers": 0, "templateLines": 0, "childComponents": 0, "flags": []}

def get_a11y_for_file(a11y_data, relative_path):
    """Get accessibility defects for a given file."""
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

def get_relative_path(absolute_path):
    """Convert absolute path to relative src/ path for matching."""
    # issue_report uses absolute paths, complexity uses relative src/ paths
    marker = os.sep + "src" + os.sep
    idx = absolute_path.replace("/", os.sep).find(marker)
    if idx != -1:
        return "src/" + absolute_path.replace("/", os.sep)[idx + len(marker):].replace(os.sep, "/")
    return ""

def generate_report():
    """Main orchestrator: load data, run passes, merge, output."""
    print("Loading static data...")
    issues_data, complexity_data, a11y_data = load_static_data()
    
    # Filter to 5 small files (< 350 lines) for Groq's context window
    files_to_process = []
    for f_node in issues_data.get("files", []):
        lines_count = f_node.get("metrics", {}).get("lines", 9999)
        if lines_count < 350:
            files_to_process.append(f_node)
        if len(files_to_process) >= 5:
            break
    
    print(f"Selected {len(files_to_process)} files for analysis.\n")
    
    final_report = []
    
    for f_node in files_to_process:
        abs_path = f_node["file"]
        filename = os.path.basename(abs_path)
        rel_path = get_relative_path(abs_path)
        
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
        
        # Add a11y defects
        a11y_defects = get_a11y_for_file(a11y_data, rel_path)
        for defect in a11y_defects:
            static_findings.append({
                "type": defect["type"],
                "category": defect["rule"],
                "severity": defect["severity"],
                "line_number": defect["line_number"],
                "element": defect["element"]
            })
        
        # Get complexity metrics
        complexity_metrics = get_complexity_for_file(complexity_data, rel_path)
        
        # Check if file exists
        if not os.path.exists(abs_path):
            print(f"  -> File not found: {abs_path}, skipping.")
            continue
        
        # Run dual-pass analysis
        pass1, pass2 = analyze_file(abs_path, static_findings, complexity_metrics)
        
        # Merge with confidence calculator
        merged = calculate_confidence(pass1, pass2)
        
        print(f"  -> Verified: {len(merged.get('verified_findings', []))} | Rejected: {len(merged.get('rejected_findings', []))}\n")
        
        final_report.append({
            "file": filename,
            "absolute_path": abs_path,
            "static_findings_fed": len(static_findings),
            "complexity_metrics": complexity_metrics,
            "verified_findings": merged.get("verified_findings", []),
            "rejected_as_false_positive": merged.get("rejected_findings", [])
        })
    
    # Write output
    output_path = os.path.join(os.path.dirname(__file__), "poc_comparison_output.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2)
    
    print(f"\nReport generated at: {output_path}")

if __name__ == "__main__":
    generate_report()
