"""
extractors/mql_extractor.py
===========================
Role in pipeline (Step 3 of 4):
    Receives the CLEANED script text from script_cleaner.py and scans it
    with regex to find every MQL API call.  Returns structured records
    suitable for insertion into the api_calls and api_flags database tables.

    THE HYBRID ARCHITECTURE — WHY THIS ORDER MATTERS:
        Step 1 (vue_parser.py)     : split .vue into blocks
        Step 2 (script_cleaner.py) : blank comments + plain strings
        Step 3 (THIS FILE)         : regex scans CLEAN text -> real calls only

    The MQL regex pattern comes from project_config.yaml so this file
    works on any module without code changes.

    MQL CALLING CONVENTION IN DIGITAL UNIVERSITY:
        new MQL().setActivity('o.[LoginCopy]').setData({...}).fetch()

    The regex must match the MQL identifier inside the preserved
    .setActivity() string argument.  After cleaning (Step 2), these strings
    survive while all other strings and all comments are blanked.

    PER-CALL CONTEXT FLAGS:
        in_mounted : True if the call lines up inside the mounted() lifecycle
                     hook.  Calls in mounted() run at page-load and are a
                     performance / coupling concern.
        in_loop    : True if the call sits inside a for-loop, forEach, or
                     a template v-for directive — repeated API calls in loops
                     are a performance risk.

    STRATEGY FOR CONTEXT DETECTION:
        tree-sitter cannot reliably parse MQL syntax in the script, so we
        use a brace-tracking pass on the raw (un-cleaned) script lines:
          1. Walk each line, counting { and } to track nesting depth.
          2. Detect the opening of a "mounted (" or "mounted()" method and
             record [start_line, end_line].
          3. Detect for-loop and forEach openings and record their ranges.
          4. For each MQL match found in the cleaned text, check whether
             its line number falls inside any of those ranges.

        This approach is O(n) in script length and never crashes on non-
        standard syntax.

Dependencies:
    pip install tree-sitter tree-sitter-language-pack PyYAML
"""

import re
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(config_path: str) -> dict:
    """
    Load and return the project_config.yaml as a dictionary.

    The config file is the single source of truth for the MQL regex pattern,
    module name, and confidence level.  This function is the only place
    where the YAML file is read — all other functions receive the config
    dict as an argument.

    Args:
        config_path (str): Path to project_config.yaml.

    Returns:
        dict: Parsed YAML contents, or an empty dict if the file cannot
              be read (a warning is logged, the pipeline continues).
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning(
            "[mql_extractor] Config file not found at '%s'. "
            "MQL extraction will use fallback defaults.", config_path
        )
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        logger.debug("[mql_extractor] Loaded config from '%s'.", config_path)
        return cfg
    except yaml.YAMLError as exc:
        logger.warning(
            "[mql_extractor] Failed to parse config YAML (%s). "
            "Using fallback defaults.", exc
        )
        return {}


# ---------------------------------------------------------------------------
# Context detection helpers (brace-tracking)
# ---------------------------------------------------------------------------

def _find_block_ranges(script_lines: list) -> tuple:
    """
    Walk the script line-by-line with brace tracking to find:
      - The line range of the mounted() lifecycle hook.
      - All for-loop and forEach line ranges.

    This function is deliberately agnostic to tree-sitter.  It uses a
    simple { } counter to track block depth, which is robust against
    non-standard MQL syntax that would confuse a proper JS parser.

    Algorithm:
        For each line, count '{' and '}' characters.  Track a running
        'depth' counter.  When we detect a line that both:
          a) matches a block-opener pattern (mounted, for, forEach, etc.)
          b) increases the depth
        we record (start_line, depth_at_open).  When depth returns to
        that saved depth, the block has closed.

    Args:
        script_lines (list[str]): Lines of the raw (or cleaned) script.

    Returns:
        tuple: (mounted_ranges, loop_ranges)
            mounted_ranges : list of (start_line_0, end_line_0) int pairs
            loop_ranges    : list of (start_line_0, end_line_0) int pairs
            (All line numbers are 0-indexed here; callers convert to 1-based)
    """
    # Regex patterns for block openers (applied to individual lines)
    MOUNTED_PAT = re.compile(
        r'\b(mounted|created)\s*\(',          # mounted ( or created(
    )
    LOOP_PAT = re.compile(
        r'\bfor\s*\('               # for( or for (
        r'|\bforEach\s*\('          # .forEach(
        r'|\bmap\s*\('              # .map(  (also repeats calls)
        r'|\bfilter\s*\('           # .filter(
        r'|v-for\s*='               # Vue template v-for directive
    )

    mounted_ranges: list = []
    loop_ranges:    list = []

    depth = 0
    # Stack entries: (start_line_0, depth_at_open, kind)
    # kind is 'mounted' or 'loop'
    open_blocks: list = []

    for line_idx, line in enumerate(script_lines):
        open_count  = line.count('{')
        close_count = line.count('}')

        # Check for new block openers BEFORE updating depth
        # (the { that opens the block is on this line)
        if open_count > 0:
            if MOUNTED_PAT.search(line):
                open_blocks.append((line_idx, depth, 'mounted'))
            elif LOOP_PAT.search(line):
                open_blocks.append((line_idx, depth, 'loop'))

        # Update depth
        depth += open_count - close_count
        if depth < 0:
            depth = 0   # guard against unbalanced braces in partial scripts

        # Check if any open blocks have now closed
        still_open = []
        for (start_l, start_depth, kind) in open_blocks:
            if depth <= start_depth:
                # Block has closed at this line
                if kind == 'mounted':
                    mounted_ranges.append((start_l, line_idx))
                else:
                    loop_ranges.append((start_l, line_idx))
            else:
                still_open.append((start_l, start_depth, kind))
        open_blocks = still_open

    # Close any blocks that reach end of file without a closing brace
    for (start_l, start_depth, kind) in open_blocks:
        end_l = len(script_lines) - 1
        if kind == 'mounted':
            mounted_ranges.append((start_l, end_l))
        else:
            loop_ranges.append((start_l, end_l))

    logger.debug(
        "[mql_extractor] Found %d mounted range(s), %d loop range(s).",
        len(mounted_ranges), len(loop_ranges)
    )
    return mounted_ranges, loop_ranges


def _in_any_range(line_0: int, ranges: list) -> bool:
    """
    Return True if line_0 (0-indexed) falls inside any of the given ranges.

    Args:
        line_0 (int)      : 0-indexed line number to test.
        ranges (list)     : List of (start_0, end_0) int pairs.

    Returns:
        bool
    """
    return any(start <= line_0 <= end for (start, end) in ranges)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_mql_calls(
    cleaned_script_text: str,
    raw_script_text: str,
    filepath: str,
    config_path: str,
) -> dict:
    """
    Extract all MQL API calls from the cleaned script text.

    Uses the regex pattern from project_config.yaml to find calls.
    For each call, determines whether it occurs inside a mounted() block
    or inside a loop construct (for, forEach, map, v-for).

    Args:
        cleaned_script_text (str): Output of script_cleaner.clean_script().
                                   Comments and non-MQL strings are blanked;
                                   .setActivity() string args are preserved.
        raw_script_text     (str): Original un-cleaned script block, used for
                                   context detection (mounted / loop ranges)
                                   because brace counting needs real code.
        filepath            (str): Path to the .vue file being analysed.
                                   Stored in every result record.
        config_path         (str): Path to project_config.yaml.

    Returns:
        dict with keys:
            "calls"   (list[dict]) : One entry per MQL match:
                {
                    "method"      : str   method name, e.g. "LoginCopy"
                    "full_match"  : str   full MQL token, e.g. "o.[LoginCopy]"
                    "in_mounted"  : bool
                    "in_loop"     : bool
                    "line_number" : int   (1-based)
                }
            "total_count"            (int)       : total matches found
            "mounted_count"          (int)       : how many are in mounted()
            "methods_with_same_name" (list[str]) : method names called > once
            "module"                 (str)       : from config
            "confidence"             (str)       : from config (HIGH/MED/LOW)
            "file"                   (str)       : filepath
    """
    cfg        = _load_config(config_path)
    module     = cfg.get("module", "unknown")
    confidence = cfg.get("mql", {}).get("confidence", "HIGH")

    # --- Read regex pattern from config (NEVER hardcoded) ---
    pattern_str = cfg.get("mql", {}).get("pattern", "")
    if not pattern_str:
        logger.warning(
            "[mql_extractor] No mql.pattern in config '%s'. "
            "Returning empty results.", config_path
        )
        return _empty_result(filepath, module, confidence)

    try:
        mql_regex = re.compile(pattern_str)
    except re.error as exc:
        logger.warning(
            "[mql_extractor] Invalid mql.pattern '%s' (%s). "
            "Returning empty results.", pattern_str, exc
        )
        return _empty_result(filepath, module, confidence)

    if not cleaned_script_text:
        logger.warning(
            "[mql_extractor] Empty cleaned_script_text for '%s'.", filepath
        )
        return _empty_result(filepath, module, confidence)

    # --- Brace-tracking context detection on RAW script ---
    # We use the raw (un-cleaned) script for this because blanked regions
    # could disrupt brace counting in edge cases.  Line numbers are identical
    # between raw and cleaned since the cleaner preserves newlines.
    raw_lines = (raw_script_text or cleaned_script_text).splitlines()
    mounted_ranges, loop_ranges = _find_block_ranges(raw_lines)

    # --- Lightweight Call Graph Analysis ---
    # 1. Collect names of all `this.methodName()` called inside mounted/created
    method_call_pat = re.compile(r'this\.([a-zA-Z0-9_$]+)\s*\(')
    mounted_methods = set()
    for (start, end) in mounted_ranges:
        for i in range(start, min(end + 1, len(raw_lines))):
            for m in method_call_pat.finditer(raw_lines[i]):
                mounted_methods.add(m.group(1))

    # 2. Find their definitions and add their line ranges to mounted_ranges
    for method_name in mounted_methods:
        def_pat = re.compile(r'^\s*(?:async\s+)?' + re.escape(method_name) + r'\s*\(')
        depth = 0
        inside = False
        start_idx = -1
        for i, line in enumerate(raw_lines):
            if not inside:
                if def_pat.search(line):
                    inside = True
                    start_idx = i
                    depth = line.count('{') - line.count('}')
            else:
                depth += line.count('{') - line.count('}')
                if depth <= 0:
                    mounted_ranges.append((start_idx, i))
                    inside = False
                    break
        if inside:  # Method reached EOF without closing brace
            mounted_ranges.append((start_idx, len(raw_lines) - 1))

    # --- Regex scan on CLEANED text ---
    clean_lines = cleaned_script_text.splitlines()
    calls: list = []

    for line_idx, line in enumerate(clean_lines):
        for match in mql_regex.finditer(line):
            method_name = match.group(1)    # captured group: the method name
            full_match  = match.group(0)    # whole token: e.g. o.[LoginCopy]
            line_number = line_idx + 1      # convert to 1-based

            in_mounted = _in_any_range(line_idx, mounted_ranges)
            in_loop    = _in_any_range(line_idx, loop_ranges)

            calls.append({
                "method":      method_name,
                "full_match":  full_match,
                "in_mounted":  in_mounted,
                "in_loop":     in_loop,
                "line_number": line_number,
            })

    # --- Summary fields ---
    total_count   = len(calls)
    mounted_count = sum(1 for c in calls if c["in_mounted"])

    # Methods called more than once (DUPLICATE_API_CALLS flag source)
    name_counts   = Counter(c["method"] for c in calls)
    duplicates    = [name for name, cnt in name_counts.items() if cnt > 1]

    logger.info(
        "[mql_extractor] '%s': %d MQL call(s), %d in mounted(), %d duplicate(s).",
        filepath, total_count, mounted_count, len(duplicates)
    )

    return {
        "file":                    filepath,
        "module":                  module,
        "confidence":              confidence,
        "calls":                   calls,
        "total_count":             total_count,
        "mounted_count":           mounted_count,
        "methods_with_same_name":  duplicates,
    }


def _empty_result(filepath: str, module: str, confidence: str) -> dict:
    """
    Return a well-formed but empty result dictionary.

    Used as a safe fallback when the config is missing or invalid, so
    callers never receive None and never need to guard against KeyErrors.

    Args:
        filepath   (str): .vue file path.
        module     (str): Module name from config.
        confidence (str): Confidence level from config.

    Returns:
        dict: Empty result with all required keys present.
    """
    return {
        "file":                   filepath,
        "module":                 module,
        "confidence":             confidence,
        "calls":                  [],
        "total_count":            0,
        "mounted_count":          0,
        "methods_with_same_name": [],
    }


# ---------------------------------------------------------------------------
# Self-test — run with: venv\Scripts\python.exe extractors\mql_extractor.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(name)s -- %(message)s",
    )

    BASE        = Path(__file__).parent.parent          # audit_tool/
    CONFIG_PATH = str(BASE / "config" / "project_config.yaml")
    SAMPLE_PATH = str(BASE / "sample" / "sample.vue")

    sys.path.insert(0, str(BASE))
    from extractors.vue_parser    import parse_vue_file
    from extractors.script_cleaner import clean_script

    print("=" * 60)
    print("mql_extractor.py self-test")
    print(f"File  : {SAMPLE_PATH}")
    print(f"Config: {CONFIG_PATH}")
    print("=" * 60)

    parsed      = parse_vue_file(SAMPLE_PATH)
    raw_script  = parsed.get("script_text") or ""
    clean       = clean_script(raw_script)

    result = extract_mql_calls(
        cleaned_script_text = clean,
        raw_script_text     = raw_script,
        filepath            = SAMPLE_PATH,
        config_path         = CONFIG_PATH,
    )

    print(f"\nmodule     : {result['module']}")
    print(f"confidence : {result['confidence']}")
    print(f"total_count: {result['total_count']}")
    print(f"mounted_count: {result['mounted_count']}")
    print(f"methods_with_same_name: {result['methods_with_same_name']}")
    print(f"\nAll calls ({len(result['calls'])}):")
    for call in result["calls"]:
        flag_str = ""
        if call["in_mounted"]: flag_str += " [MOUNTED]"
        if call["in_loop"]:    flag_str += " [IN_LOOP]"
        print(
            f"  Line {call['line_number']:>4}: "
            f"{call['full_match']:<35} method={call['method']}{flag_str}"
        )

    print()
    print("=" * 60)
    print("Self-test complete.")
    print("=" * 60)
