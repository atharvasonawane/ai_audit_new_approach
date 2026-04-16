"""
V3 Confidence Calculator (Corrected Architecture)
Merges Pass 1 (verified/rejected findings) with Pass 2 (new patterns).
"""

def calculate_confidence(pass1_result, pass2_result):
    """
    Merge Pass 1 and Pass 2 results with confidence scoring.
    
    Rules:
    - Verified static findings (Pass 1) = 85-95% confidence
    - Rejected static findings (Pass 1) = marked as false positives
    - New patterns (Pass 2) = 75% confidence
    - If Pass 1 verified + Pass 2 also found same issue = boost to 95%
    """
    merged = []
    
    # --- Process Pass 1: Verified findings ---
    verified = []
    rejected = []
    
    if pass1_result:
        verified = pass1_result.get("verified", [])
        rejected = pass1_result.get("rejected", [])
    
    for item in verified:
        confidence = item.get("confidence", 85)
        merged.append({
            "source": "pass_1_verified",
            "issue": item.get("finding", "Unknown"),
            "reason": item.get("reason", ""),
            "confidence": min(confidence, 95),
            "severity": "HIGH"
        })
    
    # --- Process Pass 2: New patterns ---
    patterns = []
    if pass2_result:
        patterns = pass2_result.get("patterns", [])
    
    for pattern in patterns:
        confidence = pattern.get("confidence", 75)
        
        # Check if Pass 1 also verified something on the same line (agreement boost)
        line = pattern.get("line", -1)
        boosted = False
        for v in verified:
            v_text = v.get("finding", "")
            if str(line) in v_text:
                # Both passes agree on the same line -> 95%
                confidence = 95
                boosted = True
                break
        
        merged.append({
            "source": "pass_2_new" if not boosted else "both_passes_agree",
            "issue": pattern.get("description", pattern.get("type", "Unknown")),
            "line": line,
            "confidence": confidence,
            "severity": "MEDIUM" if not boosted else "HIGH"
        })
    
    return {
        "verified_findings": merged,
        "rejected_findings": [
            {
                "finding": r.get("finding", "Unknown"),
                "reason": r.get("reason", ""),
                "confidence": r.get("confidence", 85)
            }
            for r in rejected
        ]
    }