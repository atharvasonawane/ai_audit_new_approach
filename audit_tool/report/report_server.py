"""
Report Server v2 — Flask app serving the comprehensive Code Audit dashboard.
Reads ALL task JSONs (task3–task7) and renders dedicated defect sections.

Usage:
    cd c:\\Users\\Atharvaso\\Desktop\\final_approach\\audit_tool
    venv\\Scripts\\python.exe report/report_server.py
"""
import os
import sys
import webbrowser
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template
from data_aggregator import load_all_data
from health_score import calculate_file_score, calculate_project_score
from ai_suggestor import generate_all_suggestions, get_suggestion

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# ===== Pre-compute all data at startup =====
print("=" * 60)
print("  Code Audit Librarian — Report Dashboard v2")
print("=" * 60)

# 1. Load all JSON data
print("\n[1/3] Loading ALL task JSONs...")
data = load_all_data()
summary = data["summary"]
files = data["files"]
category_counts = data["category_counts"]

# 2. Compute health scores for Task 7 files
print("\n[2/3] Computing health scores...")
for f in files:
    f["score"] = calculate_file_score(f)
    issues = f.get("issues", [])
    f["flag_count"] = sum(1 for i in issues if i.get("type") == "FLAG")
    f["a11y_count"] = sum(1 for i in issues if i.get("type") == "A11Y_DEFECT")
    f["ui_count"] = sum(1 for i in issues if i.get("type") == "UI_DEFECT")

total_scanned = summary.get("total_files_scanned", len(files))
project_score = calculate_project_score(files, total_scanned)
print(f"  ✓ Project health score: {project_score}/100")

# 3. Generate AI suggestions for ALL defect categories
print("\n[3/3] Generating AI suggestions...")
ai_cache = generate_all_suggestions(data)

# Attach suggestions to each defect list
for defect in data["spelling_defects"]:
    defect["ai"] = get_suggestion(ai_cache, defect)
for defect in data["css_defects"]:
    defect["ai"] = get_suggestion(ai_cache, defect)
for defect in data["placeholder_defects"]:
    defect["ai"] = get_suggestion(ai_cache, defect)
for defect in data["a11y_defects"]:
    defect["ai"] = get_suggestion(ai_cache, defect)
for defect in data["complexity_flags"]:
    defect["ai"] = get_suggestion(ai_cache, defect)

# Attach suggestions to Task 7 file issues
for f in files:
    fname = f.get("basename", "")
    f["suggestions"] = []
    for issue in f.get("issues", []):
        # Build a compatible defect dict for lookup
        lookup = {**issue, "basename": fname}
        sug = get_suggestion(ai_cache, lookup)
        f["suggestions"].append(sug)

scan_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")

print(f"\n✓ Dashboard ready!")
print(f"  Defect summary: {category_counts}")
print(f"  Opening http://localhost:5000 in your browser...\n")


@app.route("/")
def dashboard():
    return render_template(
        "report.html",
        summary=summary,
        files=files,
        project_score=project_score,
        category_counts=category_counts,
        spelling_defects=data["spelling_defects"],
        css_defects=data["css_defects"],
        placeholder_defects=data["placeholder_defects"],
        a11y_defects=data["a11y_defects"],
        complexity_flags=data["complexity_flags"],
        consistency_scores=data["consistency_scores"],
        scan_date=scan_date,
    )


def open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
