"""
Health Score Calculator — computes per-file and project-wide health scores.
"""


def calculate_file_score(file_entry):
    """
    Calculate health score (0-100) for a single file.

    Deduction rules:
        FLAG:                        -3
        A11Y_DEFECT (HIGH):          -5
        A11Y_DEFECT (MEDIUM):        -3
        UI_DEFECT (SPELLING):        -1
        UI_DEFECT (INCONSISTENT_CSS):-2
        UI_DEFECT (PLACEHOLDER_TEXT):-3
        Lines > 1000:               -10
        Lines > 500 (but ≤ 1000):   -5
        Methods > 15:               -3
    """
    score = 100
    issues = file_entry.get("issues", [])
    metrics = file_entry.get("metrics", {})

    for issue in issues:
        issue_type = issue.get("type", "")
        defect_type = issue.get("defect_type", "")
        severity = issue.get("severity", "").upper()

        if issue_type == "FLAG":
            score -= 3
        elif issue_type == "A11Y_DEFECT":
            if severity == "HIGH":
                score -= 5
            elif severity == "MEDIUM":
                score -= 3
            else:
                score -= 1
        elif issue_type == "UI_DEFECT":
            if defect_type == "SPELLING":
                score -= 1
            elif defect_type == "INCONSISTENT_CSS":
                score -= 2
            elif defect_type == "PLACEHOLDER_TEXT_IN_PRODUCTION":
                score -= 3
            else:
                score -= 1

    # Lines penalty
    lines = metrics.get("lines", 0)
    if lines > 1000:
        score -= 10
    elif lines > 500:
        score -= 5

    # Methods penalty
    methods = metrics.get("methods", 0)
    if methods > 15:
        score -= 3

    return max(0, score)


def calculate_project_score(files, total_files_scanned):
    """
    Calculate project-wide health score as weighted average.
    Clean files (not in the report) are treated as score=100.
    """
    if total_files_scanned == 0:
        return 100

    total_score = 0.0
    files_with_issues = len(files)
    clean_files = total_files_scanned - files_with_issues

    for f in files:
        total_score += calculate_file_score(f)

    # Clean files contribute 100 each
    total_score += clean_files * 100

    return round(total_score / total_files_scanned, 1)
