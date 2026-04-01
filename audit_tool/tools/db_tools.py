from langchain_core.tools import tool
import json
from tools.data_loader import get_report, get_files

def _match_file(file_path: str, search_term: str) -> bool:
    # Always work on filename only, not full path
    # Handle both backslash and forward slash
    filename = file_path.replace("\\", "/").split("/")[-1].lower()
    search = search_term.lower().strip()
    
    # Rule 1: direct containment check
    if search in filename:
        return True
    
    # Rule 2: split into words, ignore words under 
    # 3 characters, check each word against filename
    words = [w for w in search.split() if len(w) > 2]
    if words and any(w in filename for w in words):
        return True
    
    return False

# ... (Keep get_high_risk_files exactly the same) ...
@tool
def get_high_risk_files() -> str:
    """Use this tool when the developer asks which files are most dangerous, most risky, have the most issues, or should be refactored first."""
    results = []
    for f in get_files():
        if f.get("risk_level") in ["CRITICAL", "HIGH"]:
            filename = f.get("file", "").replace("\\", "/").split("/")[-1]
            issues = f.get("issues", [])
            
            flag_count = sum(1 for i in issues if i.get("type") == "FLAG")
            a11y_count = sum(1 for i in issues if i.get("type") == "A11Y_DEFECT")
            ui_count = sum(1 for i in issues if i.get("type") == "UI_DEFECT")
            
            results.append({
                "filename": filename,
                "module": f.get("module"),
                "risk_level": f.get("risk_level"),
                "flag_count": flag_count,
                "a11y_count": a11y_count,
                "ui_count": ui_count
            })
            
    return json.dumps(results)

@tool
def get_file_report(file_name: str) -> str:
    """Use this tool when the developer asks about a specific Vue file by name. Use it to get risk level, flags, defects, and metrics for that file."""
    for f in get_files():
        if _match_file(f.get("file", ""), file_name):
            return json.dumps({
                "risk_level": f.get("risk_level"),
                "module": f.get("module"),
                "metrics": f.get("metrics", {}),
                "issues": f.get("issues", []),
                "severity_summary": f.get("severity_summary", {})
            })
            
    return json.dumps({"error": "File not found", "searched_for": file_name})

@tool
def get_summary_stats() -> str:
    """Use this tool when the developer asks for an overview of the whole codebase, total files scanned, how many are critical, or general statistics."""
    report = get_report()
    return json.dumps(report.get("summary", {}))

@tool
def get_files_by_module(module_name: str) -> str:
    """Use this tool when the developer asks about a specific module or feature area of the codebase."""
    results = []
    for f in get_files():
        module = f.get("module", "")
        if module and module_name.lower() in module.lower():
            filename = f.get("file", "").replace("\\", "/").split("/")[-1]
            results.append({
                "filename": filename,
                "risk_level": f.get("risk_level"),
                "issue_count": len(f.get("issues", []))
            })
            
    if not results:
        return json.dumps({"error": "No files found for module", "module": module_name})
        
    return json.dumps(results)

@tool
def get_critical_files() -> str:
    """Use this tool when the developer asks specifically about critical files, the most dangerous files, or files that must not be touched."""
    results = []
    for f in get_files():
        if f.get("risk_level") == "CRITICAL":
            filename = f.get("file", "").replace("\\", "/").split("/")[-1]
            flags = [i.get("name") for i in f.get("issues", []) if i.get("type") == "FLAG" and "name" in i]
            
            results.append({
                "filename": filename,
                "module": f.get("module"),
                "flags": flags
            })
            
    return json.dumps(results)

@tool
def get_flag_summary() -> str:
    """Use this tool when the developer asks which flags are most common, what patterns exist across the codebase, or wants a summary of all flag types."""
    flag_counts = {}
    
    for f in get_files():
        # Using a set to count how many *files* have each unique FLAG name
        unique_flags = set(i.get("name") for i in f.get("issues", []) if i.get("type") == "FLAG" and "name" in i)
        
        for flag in unique_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
            
    sorted_flags = dict(sorted(flag_counts.items(), key=lambda item: item[1], reverse=True))
    
    return json.dumps(sorted_flags)