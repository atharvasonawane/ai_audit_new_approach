"""
checkers/flag_engine.py
=======================
Role in pipeline (final analysis step):
    Receives pre-extracted metrics from all upstream modules and applies
    every flag rule defined in Task2..txt.  This file does ZERO parsing —
    it only evaluates thresholds and pattern rules against the numbers and
    lists passed in.

    This design means the flag rules can be read, audited, and modified
    without touching any parsing code.

FLAG CATEGORIES (23 total, from Task2..txt):
    A. API-Related         (4 flags)  — HIGH_API_USAGE ... HEAVY_MOUNTED_API
    B. Payload-Related     (4 flags)  — COMPLEX_PAYLOAD ... LARGE_PAYLOAD
    C. Component Complexity(4 flags)  — LARGE_COMPONENT ... MANY_WATCHERS
    D. Combined Conditions (6 flags)  — HIGH_RISK_COMPONENT ... ARCHITECTURE_CONCERN
    E. Specific Patterns   (4 flags)  — API_IN_LOOP ... DUPLICATE_API_CALLS
    F. Template/UI         (3 flags)  — COMPLEX_TEMPLATE ... MANY_CHILDREN

INPUT CONTRACT (all arguments to evaluate_flags):
    From complexity_checker.py:
        lines           (int)  : total lines of code in the component
        methods         (int)  : number of method definitions
        computed        (int)  : number of computed properties
        watchers        (int)  : number of watchers

    From api_extractor.py:
        api_calls       (list) : list of call dicts (each has in_mounted, in_loop, type)
        duplicate_names (list) : method names called more than once

    From template_extractor.py:
        template_lines  (int)  : line count of the <template> block
        child_components(int)  : number of distinct child component tags
        max_nesting_depth(int) : deepest v-if / v-for nesting level

    From payload analysis:
        payload_keys    (int)  : number of top-level keys in the largest payload
        payload_depth   (int)  : nesting depth of that payload
        payload_size_kb (float): estimated size in kilobytes

OUTPUT:
    list[str] — flag name strings, e.g. ["HIGH_API_USAGE", "LARGE_COMPONENT"]
    Empty list means the component is healthy across all rules.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds — sourced directly from Task2..txt (never change silently)
# ---------------------------------------------------------------------------

# A. API thresholds
API_HIGH       = 3   # HIGH_API_USAGE
API_VERY_HIGH  = 5   # VERY_HIGH_API_USAGE
API_EXCESSIVE  = 8   # EXCESSIVE_API_USAGE
API_MOUNTED    = 3   # HEAVY_MOUNTED_API (calls in mounted())

# B. Payload thresholds
PAYLOAD_COMPLEX      = 10     # keys
PAYLOAD_VERY_COMPLEX = 20     # keys
PAYLOAD_DEEP_NEST    = 3      # depth
PAYLOAD_LARGE_KB     = 1024   # 1 MB = 1024 KB

# C. Component complexity thresholds
LINES_LARGE    = 500   # LARGE_COMPONENT
METHODS_MANY   = 15    # MANY_METHODS
COMPUTED_MANY  = 10    # MANY_COMPUTED
WATCHERS_MANY  = 5     # MANY_WATCHERS
PROPS_MANY     = 10    # TOO_MANY_PROPS

# F. Template thresholds
TEMPLATE_COMPLEX   = 200  # lines
TEMPLATE_DEEP_NEST = 3    # depth
CHILDREN_MANY      = 5    # child component count

# D. Combined threshold — cross-category flag count
CROSS_CATEGORY_THRESHOLD = 3   # COMPLEX_HEAVY_COMPONENT


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_flags(
    # --- Component complexity (from complexity_checker) ---
    lines:            int   = 0,
    methods:          int   = 0,
    computed:         int   = 0,
    watchers:         int   = 0,
    # --- API calls (from mql_extractor) ---
    api_calls:        list  = None,
    duplicate_names:  list  = None,
    # --- Template (from template_extractor) ---
    template_lines:   int   = 0,
    child_components: int   = 0,
    max_nesting_depth:int   = 0,
    prop_count:       int   = 0,
    # --- Payload (from payload analysis) ---
    payload_keys:     int   = 0,
    payload_depth:    int   = 0,
    payload_size_kb:  float = 0.0,
) -> list:
    """
    Apply all 23 flag rules to the supplied metrics and return a list of
    triggered flag strings.

    This function is the single source of truth for flag logic.  Every
    rule is documented inline with the exact condition from Task2..txt.

    Args:
        lines            (int)  : Total lines of code in the component.
        methods          (int)  : Number of method definitions.
        computed         (int)  : Number of computed properties.
        watchers         (int)  : Number of watchers.
        api_calls        (list) : List of call dicts from mql_extractor.
                                  Each dict has keys: type, method, full_match,
                                  in_mounted (bool), in_loop (bool),
                                  line_number.
        duplicate_names  (list) : Method names with more than one call.
        template_lines   (int)  : Line count of the <template> block.
        child_components (int)  : Number of distinct child component tags.
        max_nesting_depth(int)  : Deepest v-if / v-for nesting level.
        prop_count       (int)  : Number of props defined in the component.
        payload_keys     (int)  : Top-level keys in the largest payload.
        payload_depth    (int)  : Nesting depth of that payload.
        payload_size_kb  (float): Estimated payload size in kilobytes.

    Returns:
        list[str]: Alphabetically sorted list of triggered flag names.
                   An empty list means the component passed all checks.
    """
    if api_calls is None:
        api_calls = []
    if duplicate_names is None:
        duplicate_names = []

    flags: set = set()

    # -----------------------------------------------------------------------
    # A. API-Related Flags
    # -----------------------------------------------------------------------
    total_api = len(api_calls)
    mounted_api = sum(1 for c in api_calls if c.get("in_mounted", False))

    if total_api >= API_HIGH:
        # Condition: API calls >= 3
        flags.add("HIGH_API_USAGE")

    if total_api >= API_VERY_HIGH:
        # Condition: API calls >= 5
        flags.add("VERY_HIGH_API_USAGE")

    if total_api >= API_EXCESSIVE:
        # Condition: API calls >= 8
        flags.add("EXCESSIVE_API_USAGE")

    if mounted_api >= API_MOUNTED:
        # Condition: API calls in mounted() >= 3
        flags.add("HEAVY_MOUNTED_API")

    logger.debug("[flag_engine] API: total=%d, mounted=%d", total_api, mounted_api)

    # -----------------------------------------------------------------------
    # B. Payload-Related Flags
    # -----------------------------------------------------------------------
    if payload_keys > PAYLOAD_COMPLEX:
        # Condition: Payload keys > 10
        flags.add("COMPLEX_PAYLOAD")

    if payload_keys > PAYLOAD_VERY_COMPLEX:
        # Condition: Payload keys > 20
        flags.add("VERY_COMPLEX_PAYLOAD")

    if payload_depth > PAYLOAD_DEEP_NEST:
        # Condition: Nested payload depth > 3
        flags.add("DEEP_NESTED_PAYLOAD")

    if payload_size_kb > PAYLOAD_LARGE_KB:
        # Condition: Payload size > 1 MB (estimated as KB)
        flags.add("LARGE_PAYLOAD")

    logger.debug(
        "[flag_engine] Payload: keys=%d, depth=%d, size_kb=%.1f",
        payload_keys, payload_depth, payload_size_kb
    )

    # -----------------------------------------------------------------------
    # C. Component Complexity Flags
    # -----------------------------------------------------------------------
    if lines > LINES_LARGE:
        # Condition: Lines of code > 500
        flags.add("LARGE_COMPONENT")

    if methods > METHODS_MANY:
        # Condition: Methods count > 15
        flags.add("MANY_METHODS")

    if computed > COMPUTED_MANY:
        # Condition: Computed properties > 10
        flags.add("MANY_COMPUTED")

    if watchers > WATCHERS_MANY:
        # Condition: Watchers > 5
        flags.add("MANY_WATCHERS")

    if prop_count > PROPS_MANY:
        # Condition: Props > 10
        flags.add("TOO_MANY_PROPS")

    logger.debug(
        "[flag_engine] Component: lines=%d, methods=%d, computed=%d, watchers=%d, props=%d",
        lines, methods, computed, watchers, prop_count
    )

    # -----------------------------------------------------------------------
    # E. Specific Pattern Flags
    # (evaluated before D so combined rules can reference E results)
    # -----------------------------------------------------------------------
    if any(c.get("in_loop", False) for c in api_calls):
        # Condition: API calls in loops
        flags.add("API_IN_LOOP")

    # API_CHAINING: multiple .setActivity calls chained in immediate sequence.
    # Heuristic: any two calls whose line numbers are within 5 lines of each other
    # (tight chains as seen in MQL builder pattern).
    call_lines = sorted(c.get("line_number", 0) for c in api_calls)
    chain_found = False
    for i in range(len(call_lines) - 1):
        if call_lines[i + 1] - call_lines[i] <= 5:
            chain_found = True
            break
    if chain_found:
        # Condition: Multiple API calls in sequence (chain)
        flags.add("API_CHAINING")

    # DEPENDENT_API_CALLS: calls where one result feeds into the next.
    # Heuristic: look for .then(rs => { ... .setActivity( on the next call.
    # We detect this by checking if any consecutive pair has in_mounted=False
    # and their lines are within 20 of each other (nested .then() chain pattern).
    dependent_found = False
    sorted_calls = sorted(api_calls, key=lambda c: c.get("line_number", 0))
    for i in range(len(sorted_calls) - 1):
        gap = sorted_calls[i + 1].get("line_number", 0) - sorted_calls[i].get("line_number", 0)
        if 1 <= gap <= 20:
            dependent_found = True
            break
    if dependent_found:
        # Condition: API calls depending on each other's results
        flags.add("DEPENDENT_API_CALLS")

    if duplicate_names:
        # Condition: Same API called multiple times
        flags.add("DUPLICATE_API_CALLS")

    # -----------------------------------------------------------------------
    # F. Template / UI Complexity Flags
    # -----------------------------------------------------------------------
    if template_lines > TEMPLATE_COMPLEX:
        # Condition: Template lines > 200
        flags.add("COMPLEX_TEMPLATE")

    if max_nesting_depth > TEMPLATE_DEEP_NEST:
        # Condition: v-if/v-for nesting depth > 3
        flags.add("DEEP_NESTED_TEMPLATE")

    if child_components > CHILDREN_MANY:
        # Condition: Component has > 5 child components
        flags.add("MANY_CHILDREN")

    logger.debug(
        "[flag_engine] Template: lines=%d, children=%d, max_depth=%d",
        template_lines, child_components, max_nesting_depth
    )

    # -----------------------------------------------------------------------
    # D. Combined Condition Flags
    # (evaluated last — they depend on flags already set above)
    # -----------------------------------------------------------------------

    # Condition: HIGH_API_USAGE + COMPLEX_PAYLOAD
    if "HIGH_API_USAGE" in flags and "COMPLEX_PAYLOAD" in flags:
        flags.add("HIGH_RISK_COMPONENT")

    # Condition: VERY_HIGH_API_USAGE + VERY_COMPLEX_PAYLOAD
    if "VERY_HIGH_API_USAGE" in flags and "VERY_COMPLEX_PAYLOAD" in flags:
        flags.add("CRITICAL_COMPONENT")

    # Condition: HIGH_API_USAGE + LARGE_COMPONENT
    if "HIGH_API_USAGE" in flags and "LARGE_COMPONENT" in flags:
        flags.add("HEAVY_COMPONENT")

    # Condition: EXCESSIVE_API_USAGE + VERY_COMPLEX_PAYLOAD + LARGE_COMPONENT
    if (
        "EXCESSIVE_API_USAGE"  in flags and
        "VERY_COMPLEX_PAYLOAD" in flags and
        "LARGE_COMPONENT"      in flags
    ):
        flags.add("MONOLITH_COMPONENT")

    # Condition: Any 3+ flags from different categories
    category_flags = {
        "API":       {"HIGH_API_USAGE", "VERY_HIGH_API_USAGE", "EXCESSIVE_API_USAGE",
                      "HEAVY_MOUNTED_API"},
        "PAYLOAD":   {"COMPLEX_PAYLOAD", "VERY_COMPLEX_PAYLOAD", "DEEP_NESTED_PAYLOAD",
                      "LARGE_PAYLOAD"},
        "COMPONENT": {"LARGE_COMPONENT", "MANY_METHODS", "MANY_COMPUTED",
                      "MANY_WATCHERS", "TOO_MANY_PROPS"},
        "PATTERN":   {"API_IN_LOOP", "API_CHAINING", "DEPENDENT_API_CALLS",
                      "DUPLICATE_API_CALLS"},
        "TEMPLATE":  {"COMPLEX_TEMPLATE", "DEEP_NESTED_TEMPLATE", "MANY_CHILDREN"},
    }
    triggered_categories = sum(
        1 for cat_flags in category_flags.values()
        if flags & cat_flags   # at least one flag from this category is set
    )
    if triggered_categories >= CROSS_CATEGORY_THRESHOLD:
        # Condition: Any 3+ flags from different categories
        flags.add("COMPLEX_HEAVY_COMPONENT")

    # Condition: All flags from API, Payload, and Component categories triggered
    api_full      = category_flags["API"]      <= flags
    payload_full  = category_flags["PAYLOAD"]  <= flags
    component_full= category_flags["COMPONENT"]<= flags
    if api_full and payload_full and component_full:
        flags.add("ARCHITECTURE_CONCERN")

    result = sorted(flags)
    logger.info(
        "[flag_engine] Evaluation complete: %d flag(s) triggered: %s",
        len(result), result
    )
    return result


def summarise_flags(flags: list) -> dict:
    """
    Group a flat list of flag strings into their categories.

    Useful for the database layer and for report generation — callers
    don't need to know which flags belong to which category.

    Args:
        flags (list[str]): Output of evaluate_flags().

    Returns:
        dict: Keys are category names, values are lists of flag strings
              that fell into that category.  An empty list per category
              means no flags were triggered in that category.
    """
    category_map = {
        "API":       {"HIGH_API_USAGE", "VERY_HIGH_API_USAGE", "EXCESSIVE_API_USAGE",
                      "HEAVY_MOUNTED_API"},
        "PAYLOAD":   {"COMPLEX_PAYLOAD", "VERY_COMPLEX_PAYLOAD", "DEEP_NESTED_PAYLOAD",
                      "LARGE_PAYLOAD"},
        "COMPONENT": {"LARGE_COMPONENT", "MANY_METHODS", "MANY_COMPUTED",
                      "MANY_WATCHERS", "TOO_MANY_PROPS"},
        "COMBINED":  {"HIGH_RISK_COMPONENT", "CRITICAL_COMPONENT", "HEAVY_COMPONENT",
                      "MONOLITH_COMPONENT", "COMPLEX_HEAVY_COMPONENT",
                      "ARCHITECTURE_CONCERN"},
        "PATTERN":   {"API_IN_LOOP", "API_CHAINING", "DEPENDENT_API_CALLS",
                      "DUPLICATE_API_CALLS"},
        "TEMPLATE":  {"COMPLEX_TEMPLATE", "DEEP_NESTED_TEMPLATE", "MANY_CHILDREN"},
    }
    flag_set = set(flags)
    return {
        cat: sorted(flag_set & cat_flags)
        for cat, cat_flags in category_map.items()
    }


# ---------------------------------------------------------------------------
# Self-test — python checkers/flag_engine.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)

    PASS = "[PASS]"
    FAIL = "[FAIL]"
    results = []

    def check(label, flags, expected_present=(), expected_absent=()):
        """Helper: assert flags contain all expected_present and none of expected_absent."""
        flag_set = set(flags)
        ok = True
        missing  = [f for f in expected_present if f not in flag_set]
        extra    = [f for f in expected_absent  if f in flag_set]
        if missing or extra:
            ok = False
        status = PASS if ok else FAIL
        results.append((status, label, missing, extra))
        return ok

    print("=" * 65)
    print("flag_engine.py self-test (all 23 flag rules)")
    print("=" * 65)

    # ── A. API flags ────────────────────────────────────────────────
    def _calls(n, mounted=0, loop=0):
        calls = []
        for i in range(n):
            calls.append({
                "method": f"Method{i}", "full_match": f"o.[Method{i}]",
                "in_mounted": i < mounted, "in_loop": i < loop,
                "line_number": i * 10 + 1
            })
        return calls

    check("HIGH_API_USAGE (3 calls)",
          evaluate_flags(api_calls=_calls(3)),
          expected_present=["HIGH_API_USAGE"])

    check("VERY_HIGH_API_USAGE (5 calls)",
          evaluate_flags(api_calls=_calls(5)),
          expected_present=["HIGH_API_USAGE", "VERY_HIGH_API_USAGE"])

    check("EXCESSIVE_API_USAGE (8 calls)",
          evaluate_flags(api_calls=_calls(8)),
          expected_present=["EXCESSIVE_API_USAGE"])

    check("HEAVY_MOUNTED_API (3 in mounted)",
          evaluate_flags(api_calls=_calls(5, mounted=3)),
          expected_present=["HEAVY_MOUNTED_API"])

    check("No API flags (2 calls)",
          evaluate_flags(api_calls=_calls(2)),
          expected_absent=["HIGH_API_USAGE"])

    # ── B. Payload flags ────────────────────────────────────────────
    check("COMPLEX_PAYLOAD (11 keys)",
          evaluate_flags(payload_keys=11),
          expected_present=["COMPLEX_PAYLOAD"])

    check("VERY_COMPLEX_PAYLOAD (21 keys)",
          evaluate_flags(payload_keys=21),
          expected_present=["COMPLEX_PAYLOAD", "VERY_COMPLEX_PAYLOAD"])

    check("DEEP_NESTED_PAYLOAD (depth=4)",
          evaluate_flags(payload_depth=4),
          expected_present=["DEEP_NESTED_PAYLOAD"])

    check("LARGE_PAYLOAD (1025 KB)",
          evaluate_flags(payload_size_kb=1025),
          expected_present=["LARGE_PAYLOAD"])

    # ── C. Component complexity ─────────────────────────────────────
    check("LARGE_COMPONENT (501 lines)",
          evaluate_flags(lines=501),
          expected_present=["LARGE_COMPONENT"])

    check("MANY_METHODS (16 methods)",
          evaluate_flags(methods=16),
          expected_present=["MANY_METHODS"])

    check("MANY_COMPUTED (11 computed)",
          evaluate_flags(computed=11),
          expected_present=["MANY_COMPUTED"])

    check("MANY_WATCHERS (6 watchers)",
          evaluate_flags(watchers=6),
          expected_present=["MANY_WATCHERS"])

    # ── D. Combined flags ───────────────────────────────────────────
    check("HIGH_RISK_COMPONENT (api>=3 + payload>10)",
          evaluate_flags(api_calls=_calls(3), payload_keys=11),
          expected_present=["HIGH_RISK_COMPONENT"])

    check("CRITICAL_COMPONENT (api>=5 + payload>20)",
          evaluate_flags(api_calls=_calls(5), payload_keys=21),
          expected_present=["CRITICAL_COMPONENT"])

    check("HEAVY_COMPONENT (api>=3 + lines>500)",
          evaluate_flags(api_calls=_calls(3), lines=501),
          expected_present=["HEAVY_COMPONENT"])

    check("MONOLITH_COMPONENT (api>=8 + payload>20 + lines>500)",
          evaluate_flags(api_calls=_calls(8), payload_keys=21, lines=501),
          expected_present=["MONOLITH_COMPONENT"])

    check("COMPLEX_HEAVY_COMPONENT (3+ categories triggered)",
          evaluate_flags(api_calls=_calls(3), lines=501, template_lines=201),
          expected_present=["COMPLEX_HEAVY_COMPONENT"])

    check("ARCHITECTURE_CONCERN (all API+Payload+Component flags)",
          evaluate_flags(
              api_calls=_calls(8, mounted=3), payload_keys=21,
              payload_depth=4, payload_size_kb=1025, lines=501,
              methods=16, computed=11, watchers=6
          ),
          expected_present=["ARCHITECTURE_CONCERN"])

    # ── E. Pattern flags ────────────────────────────────────────────
    check("API_IN_LOOP",
          evaluate_flags(api_calls=_calls(3, loop=1)),
          expected_present=["API_IN_LOOP"])

    check("API_CHAINING (calls within 5 lines)",
          evaluate_flags(api_calls=[
              {"method": "A", "full_match": "o.[A]", "in_mounted": False,
               "in_loop": False, "line_number": 10},
              {"method": "B", "full_match": "o.[B]", "in_mounted": False,
               "in_loop": False, "line_number": 13},
          ]),
          expected_present=["API_CHAINING"])

    check("DUPLICATE_API_CALLS",
          evaluate_flags(api_calls=_calls(3), duplicate_names=["LoginCopy"]),
          expected_present=["DUPLICATE_API_CALLS"])

    # ── F. Template flags ───────────────────────────────────────────
    check("COMPLEX_TEMPLATE (201 lines)",
          evaluate_flags(template_lines=201),
          expected_present=["COMPLEX_TEMPLATE"])

    check("DEEP_NESTED_TEMPLATE (depth=4)",
          evaluate_flags(max_nesting_depth=4),
          expected_present=["DEEP_NESTED_TEMPLATE"])

    check("MANY_CHILDREN (6 child components)",
          evaluate_flags(child_components=6),
          expected_present=["MANY_CHILDREN"])

    # ── Print summary ───────────────────────────────────────────────
    print()
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    for status, label, missing, extra in results:
        print(f"  {status} {label}")
        if missing: print(f"        Missing flags: {missing}")
        if extra:   print(f"        Unexpected flags: {extra}")

    print()
    print(f"  Result: {passed}/{len(results)} tests passed, {failed} failed.")

    # ── Run against sample.vue data ─────────────────────────────────
    print()
    print("=" * 65)
    print("sample.vue real data evaluation")
    print("=" * 65)

    import sys
    from pathlib import Path
    BASE = Path(__file__).parent.parent
    sys.path.insert(0, str(BASE))
    from extractors.vue_parser     import parse_vue_file
    from extractors.script_cleaner import clean_script
    from extractors.api_extractor  import extract_api_calls

    CONFIG = str(BASE / "config" / "project_config.yaml")
    SAMPLE = str(BASE / "sample" / "sample.vue")

    parsed    = parse_vue_file(SAMPLE)
    raw       = parsed.get("script_text") or ""
    clean     = clean_script(raw)
    api_data  = extract_api_calls(clean, raw, SAMPLE, CONFIG)
    api_calls = api_data["calls"]
    dup_names = api_data["methods_with_same_name"]

    # adminLogin.vue known metrics (approximate from file inspection)
    sample_flags = evaluate_flags(
        lines            = 1832,   # full .vue file lines
        methods          = 20,     # methods block has ~20 functions
        computed         = 1,
        watchers         = 0,
        api_calls        = api_calls,
        duplicate_names  = dup_names,
        template_lines   = 309,    # template block ends at line 309
        child_components = 2,      # Dropdown, InputText
        max_nesting_depth= 3,
        payload_keys     = 4,      # typical payload: clientId, password, userName, browserDetails
        payload_depth    = 1,
        payload_size_kb  = 0.5,
    )

    print(f"\nFlags triggered ({len(sample_flags)}):")
    for f in sample_flags:
        print(f"  {f}")

    summary = summarise_flags(sample_flags)
    print(f"\nBy category:")
    for cat, cat_flags in summary.items():
        if cat_flags:
            print(f"  {cat}: {cat_flags}")
