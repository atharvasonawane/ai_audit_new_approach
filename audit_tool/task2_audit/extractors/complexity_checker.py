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
_RE_METHOD_KEY = re.compile(r"^\s{2,}(\w+)\s*\(", re.MULTILINE)
_RE_COMPUTED_KEY = re.compile(r"^\s{2,}(\w+)\s*\(\s*\)", re.MULTILINE)
_RE_WATCHER_KEY = re.compile(r"^\s{2,}'?[\w.]+'?\s*[:(]", re.MULTILINE)

# Options API top-level block names
_METHODS_KEYS = {"methods"}
_COMPUTED_KEYS = {"computed"}
_WATCH_KEYS = {"watch"}
_METHOD_EXCLUDE = {"data", "created", "mounted", "computed", "watch"}

# ---------------------------------------------------------------------------
# tree-sitter setup
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language as _get_ts_language

    _TS_AVAILABLE = True
    _JS_LANGUAGE = _get_ts_language("javascript")
except ImportError:
    _TS_AVAILABLE = False
    _JS_LANGUAGE = None
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

    # 2. Parse methods:{} directly from script text (robust to AST ERROR nodes)
    methods = _count_methods_from_methods_block(script_text)

    # 3. Try tree-sitter AST walk for computed/watchers
    computed = 0
    watchers = 0

    if _TS_AVAILABLE and _JS_LANGUAGE:
        source_bytes = script_text.encode("utf-8", errors="replace")
        try:
            parser = Parser(_JS_LANGUAGE)
            tree = parser.parse(source_bytes)
            root = tree.root_node

            ast_methods = _count_methods_object_from_ast(root, source_bytes)
            if ast_methods > 0:
                methods = ast_methods

            _, computed, watchers = _count_from_ast(root, source_bytes)
            logger.debug(
                "[complexity_checker] AST (Options API): methods=%d computed=%d watchers=%d",
                methods,
                computed,
                watchers,
            )

            # If Options API found nothing, try Composition API counting.
            # In <script setup> or defineComponent({ setup() {...} }), there's
            # no methods/computed/watch object — instead they use function calls.
            if computed == 0 and watchers == 0:
                comp_m, comp_c, comp_w = _count_composition_api(root, source_bytes)
                if comp_c > 0 or comp_w > 0:
                    if methods == 0:
                        methods = comp_m
                    computed = comp_c
                    watchers = comp_w
                    logger.debug(
                        "[complexity_checker] AST (Composition API): methods=%d computed=%d watchers=%d",
                        methods,
                        computed,
                        watchers,
                    )
        except Exception as exc:
            logger.warning(
                "[complexity_checker] AST walk failed (%s); using regex.", exc
            )
            _, computed, watchers = _count_from_regex(script_text)
    else:
        _, computed, watchers = _count_from_regex(script_text)

    # If AST found nothing (all ERROR nodes), fall back to regex
    if computed == 0 and watchers == 0:
        logger.debug("[complexity_checker] AST returned zeros; trying regex fallback.")
        _, regex_c, regex_w = _count_from_regex(script_text)
        computed = regex_c
        watchers = regex_w

    return {
        "lines": lines,
        "methods": methods,
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
    methods = 0
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


def _count_methods_object_from_ast(root, source_bytes: bytes) -> int:
    """Count function-valued top-level entries in methods: { ... } from AST."""
    export_obj = _find_export_default_object(root, source_bytes)
    if export_obj is None:
        return 0

    for prop in _get_object_properties(export_obj):
        key = _get_property_key(prop, source_bytes)
        if key != "methods":
            continue

        methods_obj = _get_property_value(prop)
        if methods_obj is None:
            return 0

        count = 0
        for child in methods_obj.children:
            if child.type == "method_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = (
                        source_bytes[name_node.start_byte : name_node.end_byte]
                        .decode("utf-8", errors="replace")
                        .strip("'\"")
                    )
                    if name not in _METHOD_EXCLUDE:
                        count += 1
            elif child.type == "pair":
                name = _get_property_key(child, source_bytes)
                if not name or name in _METHOD_EXCLUDE:
                    continue
                value_node = child.child_by_field_name("value")
                if value_node and value_node.type in (
                    "function",
                    "function_expression",
                    "arrow_function",
                    "generator_function",
                ):
                    count += 1
        return count

    return 0


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
            text = source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8", errors="replace"
            )
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
        1
        for c in obj_node.children
        if c.type in ("pair", "method_definition", "shorthand_property_identifier")
    )


# ---------------------------------------------------------------------------
# Composition API counting (Vue 3 <script setup>)
# ---------------------------------------------------------------------------

# Function names that count as "computed" in Composition API
_COMPOSITION_COMPUTED = {"computed"}
# Function names that count as "watchers" in Composition API
_COMPOSITION_WATCHERS = {"watch", "watchEffect", "watchPostEffect", "watchSyncEffect"}


def _count_composition_api(root, source_bytes: bytes) -> tuple:
    """
    Count metrics for Vue 3 Composition API / <script setup> components.

    In Composition API, there are no methods/computed/watch objects.
    Instead:
        - methods = top-level function declarations and const arrow/function expressions
        - computed = calls to computed(() => ...)
        - watchers = calls to watch() / watchEffect()

    Returns:
        tuple: (methods_count, computed_count, watchers_count)
    """
    methods = 0
    computed = 0
    watchers = 0

    def _walk(node):
        nonlocal methods, computed, watchers

        # Count function declarations at top level: function foo() { ... }
        if node.type == "function_declaration":
            methods += 1

        # Count const arrow/function expressions: const foo = () => { ... }
        # These appear as: lexical_declaration > variable_declarator > arrow_function/function
        if node.type == "variable_declarator":
            for child in node.children:
                if child.type in ("arrow_function", "function_expression", "function"):
                    methods += 1
                    break

        # Count calls to computed(), watch(), watchEffect()
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn and fn.type == "identifier":
                fn_name = source_bytes[fn.start_byte : fn.end_byte].decode(
                    "utf-8", errors="replace"
                )
                if fn_name in _COMPOSITION_COMPUTED:
                    computed += 1
                elif fn_name in _COMPOSITION_WATCHERS:
                    watchers += 1

        for child in node.children:
            _walk(child)

    _walk(root)
    return methods, computed, watchers


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
    methods = _regex_count_block(script_text, r"\bmethods\s*:\s*\{")
    computed = _regex_count_block(script_text, r"\bcomputed\s*:\s*\{")
    watchers = _regex_count_block(script_text, r"\bwatch\s*:\s*\{")
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
        if ch == "{":
            depth += 1
        elif ch == "}":
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
        inner_depth += stripped.count("{") - stripped.count("}")
        if inner_depth == 1:  # direct children of the block
            if re.match(r"^'?[\w$]+'?\s*[:(]", stripped):
                count += 1

    return count


def _count_methods_from_methods_block(script_text: str) -> int:
    """
    Count top-level function entries inside methods: { ... } only.

    Counts:
        - shorthand methods: foo() {}, async foo() {}
        - function props: foo: function() {}, foo: async function() {}
        - arrow props: foo: () => {}, foo: async () => {}

    Excludes lifecycle hook-like names and nested function declarations.
    """
    total = 0
    for block in _find_named_object_blocks(script_text, "methods"):
        total += _count_top_level_method_entries(block)
    return total


def _find_named_object_blocks(script_text: str, block_name: str) -> list:
    pattern = re.compile(rf"\b{re.escape(block_name)}\s*:\s*\{{")
    blocks = []

    for m in pattern.finditer(script_text):
        open_brace = script_text.find("{", m.start())
        if open_brace < 0:
            continue

        end_idx = _find_matching_brace(script_text, open_brace)

        if end_idx > open_brace:
            blocks.append(script_text[open_brace + 1 : end_idx])

    return blocks


def _count_top_level_method_entries(methods_block: str) -> int:
    count = 0
    depth = 0
    chunk_start = 0

    for i, ch in enumerate(methods_block):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "," and depth == 0:
            if _is_function_method_entry(methods_block[chunk_start:i]):
                count += 1
            chunk_start = i + 1

    if _is_function_method_entry(methods_block[chunk_start:]):
        count += 1

    return count


def _is_function_method_entry(segment: str) -> bool:
    text = segment.strip()
    if not text:
        return False

    shorthand = re.match(
        r"^(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{",
        text,
    )
    if shorthand:
        return shorthand.group(1) not in _METHOD_EXCLUDE

    prop = re.match(
        r"^['\"]?([A-Za-z_$][\w$]*)['\"]?\s*:\s*(.*)$",
        text,
        flags=re.DOTALL,
    )
    if not prop:
        return False

    name = prop.group(1)
    if name in _METHOD_EXCLUDE:
        return False

    value = prop.group(2).strip()
    return (
        re.match(r"^(?:async\s+)?function\b", value) is not None
        or re.match(r"^(?:async\s+)?\([^)]*\)\s*=>", value) is not None
        or re.match(r"^(?:async\s+)?[A-Za-z_$][\w$]*\s*=>", value) is not None
    )


def _find_matching_brace(text: str, open_brace_idx: int) -> int:
    """Find matching closing brace while ignoring strings/comments."""
    depth = 0
    i = open_brace_idx
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_single:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue
        if in_template:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_template = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == "`":
            in_template = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return -1


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, logging
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-8s %(name)s -- %(message)s"
    )

    BASE = Path(__file__).parent.parent
    SAMPLE_PATH = str(BASE / "sample" / "sample.vue")

    sys.path.insert(0, str(BASE))
    from extractors.vue_parser import parse_vue_file

    parsed = parse_vue_file(SAMPLE_PATH)
    raw = parsed.get("script_text") or ""

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

    Path(BASE / "_complexity_results.txt").write_text("\n".join(out), encoding="utf-8")
    print("Saved to _complexity_results.txt")
