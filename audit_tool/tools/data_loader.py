import json
from pathlib import Path

# Resolve the path to task7/issue_report.json relative to this file's location
REPORT_PATH = Path(__file__).resolve().parent.parent / "task7" / "issue_report.json"

def _load_report():
    if not REPORT_PATH.exists():
        raise FileNotFoundError(f"Issue report not found at: {REPORT_PATH}")
    
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse issue report. Malformed JSON: {e}")

# Load at import time so disk is only read once per session
_report = _load_report()

def get_report():
    return _report

def get_files():
    return _report.get("files", [])