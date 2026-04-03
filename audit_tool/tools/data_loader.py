import json
import os
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

def clear_cache():
    # Stub to prevent NameError, as session cache is handled at the agent level
    pass

_report = None
_report_mtime = None

def get_report():
    global _report, _report_mtime
    
    current_mtime = os.path.getmtime(REPORT_PATH)
    if _report_mtime != current_mtime:
        _report = _load_report()
        _report_mtime = current_mtime
        print("[REPORT] Detected change — reloaded from disk.")
        clear_cache()
        
    return _report

def get_files():
    return get_report().get("files", [])