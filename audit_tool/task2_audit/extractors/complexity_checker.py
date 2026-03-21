"""
extractors/complexity_checker.py
=================================
Role in pipeline (feeds into flag_engine.py):
    Counts structural complexity metrics from the raw <script> text of a
    Vue component.  These numbers are passed directly to flag_engine
    evaluate_flags() and compared against Task2..txt thresholds.

    Metrics produced:
        lines    (int) : total non-blank lines in the script block
        methods  (int) : number of method function definitions
        computed (int) : number of computed property definitions
        watchers (int) : number of watcher definitions

    HOW EACH IS COUNTED:
        Lines    — split on newlines, discard blank/whitespace-only lines.
        Methods  — tree-sitter walks the AST for the methods: {} object;
                   counts every pair_field (key: function) inside it.
                   Falls back to regex if tree-sitter produces ERROR nodes
                   over the whole script.
        Computed — same walk inside the computed: {} object.
        Watchers — same walk inside the watch: {} object.

    GRACEFUL DEGRADATION:
        Since MQL syntax produces ERROR nodes in tree-sitter, we use a
        two-pass strategy:
          1. Try tree-sitter AST walk to find Options API objects.
          2. If the object is not found in the AST (all-ERROR script),
             fall back to counting with conservative regex.

Dependencies:
    pip install tree-sitter tree-sitter-language-pack
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex fallbacks (used when tree-sitter AST walk can't find the block)
# ---------------------------------------------------------------------------
_RE_METHOD_KEY    = re.compile(r'^\s{2,}(\w+)\s*\(', re.MULTILINE)
_RE_COMPUTED_KEY  = re.compile(r'^\s{2,}(\w+)\s*\(\s*\)', re.MULTILINE)
_RE_WATCHER_KEY   = re.compile(r"^\s{2,}'?[\w.]+'?\s*[:(]", re.MULTILINE)

# Options API top-level block names
_METHODS_KEYS   = {"methods"}
_COMPUTED_KEYS  = {"computed"}
_WATCH_KEYS     = {"watch"}

# ---------------------------------------------------------------------------
# tree-sitter setup
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language as _get_ts_language
    _TS_AVAILABLE = True
    _JS_LANGUAGE  = _get_ts_language("javascript")
except ImportError:
    _TS_AVAILABLE = False
    _JS_LANGUAGE  = None
    logger.warning("[complexity_checker] tree-sitter not installed.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_complexity(script_text: str) -> dict:
    """
    Count complexity metrics from raw <script> block text.

    Args:
        script_text (str): Raw script text from vue_parser.parse_vue_file().

    Returns:
        dict with keys:
            lines    (int): Non-blank script lines.
            methods  (int): Method definitions in methods: {}.
            computed (int): Computed properties in computed: {}.
            watchers (int): Watcher definitions in watch: {}.
    """
    if not script_text:
        return {"lines": 0, "methods": 0, "computed": 0, "watchers": 0}

    # 1. Line count — straightforward
    lines = sum(1 for l in script_text.splitlines() if l.strip())

    # 2. Try tree-sitter AST walk first
    methods  = 0
    computed = 0
    watchers = 0

    if _TS_AVAILABLE and _JS_LANGUAGE:
        source_bytes = script_text.encode("utf-8", errors="replace")
        try:
            parser = Parser(_JS_LANGUAGE)
            tree   = parser.parse(source_bytes)
            root   = tree.root_node

            methods, computed, watchers = _count_from_ast(root, source_bytes)
            logger.debug(
                "[complexity_checker] AST: methods=%d computed=%d watchers=%d",
                methods, computed, watchers
            )
        except Exception as exc:
            logger.warning("[complexity_checker] AST walk failed (%s); using regex.", exc)
            methods, computed, watchers = _count_from_regex(script_text)
    else:
        methods, computed, watchers = _count_from_regex(script_text)

    # If AST found nothing (all ERROR nodes), fall back to regex
    if methods == 0 and computed == 0 and watchers == 0:
        logger.debug("[complexity_checker] AST returned zeros; trying regex fallback.")
        regex_m, regex_c, regex_w = _count_from_regex(script_text)
        methods  = regex_m
        computed = regex_c
        watchers = regex_w

    return {
        "lines":    lines,
        "methods":  methods,
        "computed": computed,
        "watchers": watchers,
    }


# ---------------------------------------------------------------------------
# AST-based counting
# ---------------------------------------------------------------------------

def _count_from_ast(root, source_bytes: bytes) -> tuple:
    """
    Walk the tree-sitter AST to find Options API objects and count entries.

    Returns:
        tuple: (methods_count, computed_count, watchers_count)
    """
    methods  = 0
    computed = 0
    watchers = 0

    # Find the default export object: export default { ... }
    export_obj = _find_export_default_object(root, source_bytes)
    if export_obj is None:
        return methods, computed, watchers

    # Walk the top-level properties of the export default object
    for prop in _get_object_properties(export_obj):
        key = _get_property_key(prop, source_bytes)
        if not key:
            continue

        if key in _METHODS_KEYS:
            value = _get_property_value(prop)
            methods = _count_object_keys(value) if value else 0

        elif key in _COMPUTED_KEYS:
            value = _get_property_value(prop)
            computed = _count_object_keys(value) if value else 0

        elif key in _WATCH_KEYS:
            value = _get_property_value(prop)
            watchers = _count_object_keys(value) if value else 0

    return methods, computed, watchers


def _find_export_default_object(root, source_bytes: bytes):
    """
    Find the object literal node in `export default { ... }`.
    Returns the object node, or None if not found.
    """
    for child in root.children:
        if child.type == "export_statement":
            for sub in child.children:
                if sub.type == "object":
                    return sub
    return None


def _get_object_properties(obj_node):
    """Yield all pair / method_definition children of an object node."""
    if obj_node is None:
        return
    for child in obj_node.children:
        if child.type in ("pair", "method_definition", "shorthand_property_identifier"):
            yield child


def _get_property_key(prop_node, source_bytes: bytes) -> str:
    """Extract the string key name of a property node."""
    for child in prop_node.children:
        if child.type in ("property_identifier", "identifier", "string"):
            text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return text.strip("'\"")
    return ""


def _get_property_value(prop_node):
    """Return the value node of a pair (the object after the colon)."""
    children = list(prop_node.children)
    # pair: [key, ':', value]  — value is the last child that is an object
    for child in reversed(children):
        if child.type == "object":
            return child
    return None


def _count_object_keys(obj_node) -> int:
    """Count how many properties are in an object literal."""
    if obj_node is None:
        return 0
    return sum(
        1 for c in obj_node.children
        if c.type in ("pair", "method_definition", "shorthand_property_identifier")
    )


# ---------------------------------------------------------------------------
# Regex fallback counting
# ---------------------------------------------------------------------------

def _count_from_regex(script_text: str) -> tuple:
    """
    Conservative regex-based counting when the AST walk cannot find blocks.

    Finds the methods: {}, computed: {}, watch: {} blocks by locating
    their opening brace and counting top-level keys (2+ spaces indent,
    followed by identifier and opening paren or colon).

    Returns:
        tuple: (methods_count, computed_count, watchers_count)
    """
    methods  = _regex_count_block(script_text, r'\bmethods\s*:\s*\{')
    computed = _regex_count_block(script_text, r'\bcomputed\s*:\s*\{')
    watchers = _regex_count_block(script_text, r'\bwatch\s*:\s*\{')
    return methods, computed, watchers


def _regex_count_block(script_text: str, block_pattern: str) -> int:
    """
    Find a named Options API block and count its direct top-level entries.

    Extracts the content between the opening { and matching closing }
    of the first match of block_pattern, then counts lines that look
    like property definitions (indented identifier followed by ( or :).

    Args:
        script_text   (str): Full script text.
        block_pattern (str): Regex pattern that locates the block start.

    Returns:
        int: Estimated count of top-level entries in that block.
    """
    match = re.search(block_pattern, script_text)
    if not match:
        return 0

    start = match.end() - 1  # position of the opening {
    depth = 0
    block_chars = []

    for i, ch in enumerate(script_text[start:], start=start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
        block_chars.append(ch)

    block = "".join(block_chars)

    # Count direct children: lines at depth-1 that are identifier-like
    count = 0
    inner_depth = 0
    for line in block.splitlines():
        stripped = line.strip()
        inner_depth += stripped.count('{') - stripped.count('}')
        if inner_depth == 1:   # direct children of the block
            if re.match(r"^'?[\w$]+'?\s*[:(]", stripped):
                count += 1

    return count


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, logging
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s -- %(message)s")

    BASE        = Path(__file__).parent.parent
    SAMPLE_PATH = str(BASE / "sample" / "sample.vue")

    sys.path.insert(0, str(BASE))
    from extractors.vue_parser import parse_vue_file

    parsed = parse_vue_file(SAMPLE_PATH)
    raw    = parsed.get("script_text") or ""

    result = check_complexity(raw)

    out = []
    out.append("=== complexity_checker.py self-test ===")
    out.append(f"File  : {SAMPLE_PATH}")
    out.append(f"lines    : {result['lines']}")
    out.append(f"methods  : {result['methods']}")
    out.append(f"computed : {result['computed']}")
    out.append(f"watchers : {result['watchers']}")

    for line in out:
        print(line)

    Path(BASE / "_complexity_results.txt").write_text(
        "\n".join(out), encoding="utf-8"
    )
    print("Saved to _complexity_results.txt")
