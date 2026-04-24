"""
extractors/script_cleaner.py
============================
Role in pipeline (Step 2 of 4):
    Receives the raw <script> text from vue_parser.py and returns a
    CLEANED version that prevents false positives in MQL regex scanning.

    In the Digital University codebase, MQL calls follow this convention:

        new MQL().setActivity('o.[LoginCopy]').setData({...}).fetch()

    The MQL method identifier is ALWAYS a string argument to .setActivity().
    This means we CANNOT blindly strip all strings — doing so removes the
    very MQL names we need to find.

    SMART STRIPPING STRATEGY:
        Strip (blank with spaces):
            - All /* */ and // comments
            - All string literals NOT inside a .setActivity(...) call
            - All template literals

        Preserve:
            - Strings that ARE the argument to .setActivity(...)
              e.g.  'o.[LoginCopy]'  in  .setActivity('o.[LoginCopy]')

    WHY THIS IS CORRECT:

        INPUT::
            // OLD CODE - o.[LoginCopy](old_data)          <- comment: STRIP
            let msg = "please call o.[LoginCopy] here"    <- plain string: STRIP
            new MQL().setActivity('o.[LoginCopy]')        <- setActivity arg: KEEP

        After cleaning, regex finds 1 real MQL call. Not 3.

    HOW setActivity ARGS ARE IDENTIFIED:
        tree-sitter parses  .setActivity('o.[LoginCopy]')  as:
            call_expression
              member_expression
                property_identifier  "setActivity"
              arguments
                string  'o.[LoginCopy]'  <- this is what we keep

Dependencies:
    pip install tree-sitter tree-sitter-language-pack
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node types to strip
# ---------------------------------------------------------------------------
COMMENT_NODE_TYPES: frozenset = frozenset(
    {
        "comment",  # // single-line  and  /* multi-line */
    }
)

STRING_NODE_TYPES: frozenset = frozenset(
    {
        "string",  # 'single' and "double" quoted literals
        "template_string",  # `backtick template literals`
    }
)

STRIP_NODE_TYPES: frozenset = COMMENT_NODE_TYPES | STRING_NODE_TYPES

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
    logger.warning(
        "[script_cleaner] tree-sitter not installed. "
        "Run: pip install tree-sitter tree-sitter-language-pack"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clean_script(raw_script_text: str) -> str:
    """
    Remove comments and non-MQL string literals from a Vue <script> block.

    Strips all comments and string literals EXCEPT strings that are the
    direct argument to a .setActivity(...) call — because in the Digital
    University codebase, all MQL method identifiers live inside
    .setActivity('o.[MethodName]') strings.

    Example
    -------
    INPUT::

        // OLD CODE - o.[LoginCopy](old_data)
        let msg = "please call o.[LoginCopy] here"
        new MQL().setActivity('o.[LoginCopy]').fetch()

    OUTPUT after clean_script()::

        new MQL().setActivity('o.[LoginCopy]').fetch()

    The MQL regex then finds exactly 1 real call, not 3.

    Args:
        raw_script_text (str): Raw text of the <script> block from
                               vue_parser.parse_vue_file().

    Returns:
        str: Cleaned script text. Falls back to raw on error — never crashes.
    """
    if not raw_script_text:
        logger.debug("[script_cleaner] Empty script; returning as-is.")
        return raw_script_text

    if not _TS_AVAILABLE or _JS_LANGUAGE is None:
        logger.warning(
            "[script_cleaner] tree-sitter unavailable — returning raw script."
        )
        return raw_script_text

    source_bytes = raw_script_text.encode("utf-8", errors="replace")

    try:
        parser = Parser(_JS_LANGUAGE)
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.warning("[script_cleaner] Parse failed (%s). Returning raw text.", exc)
        return raw_script_text

    root = tree.root_node
    if root is None:
        logger.warning("[script_cleaner] root_node is None; returning raw text.")
        return raw_script_text

    intervals: list = []
    _collect_strip_intervals(root, source_bytes, intervals)

    if not intervals:
        logger.debug("[script_cleaner] Nothing to strip; returning as-is.")
        return raw_script_text

    cleaned = _blank_intervals(source_bytes, intervals)

    logger.debug(
        "[script_cleaner] Stripped %d region(s). Raw=%d, Cleaned=%d chars.",
        len(intervals),
        len(raw_script_text),
        len(cleaned),
    )
    return cleaned


def get_strip_node_types() -> frozenset:
    """
    Return the set of node types this cleaner targets.

    Returns:
        frozenset: All node types subject to stripping.
    """
    return STRIP_NODE_TYPES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_preserved_string(node, source_bytes: bytes) -> bool:
    """
    Return True if this string node is inside an API call or an object structure.

    This preserves:
      1. All strings inside object literals `{ ... }` (ensures JSON payloads survive)
      2. All strings inside API function calls (`fetch`, `axios`, `$http`, `setData`)
      3. The MQL string identifier inside `.setActivity(...)`
    """
    curr = node.parent
    while curr is not None:
        # Don't look too far up the tree (e.g. past the current statement)
        if curr.type in [
            "expression_statement",
            "variable_declarator",
            "return_statement",
        ]:
            # We hit the boundary of the current statement.
            pass

        # 1. Inside an object literal (e.g., payload body)
        if curr.type == "object":
            return True

        # 2. Inside a function call, let's check its name
        if curr.type == "call_expression":
            func_node = curr.child_by_field_name("function")
            if func_node is not None:
                func_name = source_bytes[
                    func_node.start_byte : func_node.end_byte
                ].decode("utf-8", errors="replace")
                valid_funcs = ["setActivity", "setData", "fetch", "axios", "$http"]
                if any(v in func_name for v in valid_funcs):
                    return True

        # Stop traversing up if we hit the block or statement edge
        # This prevents it from thinking a random `let message = "Hello"`
        # is inside the root object `{}` of the Vue component.
        if curr.type == "method_definition" or curr.type == "function_declaration":
            break

        curr = curr.parent

    return False


def _collect_strip_intervals(node, source_bytes: bytes, intervals: list) -> None:
    """
    Recursively walk the AST and record byte ranges to blank.

    - Comments are always stripped.
    - String/template literals are stripped UNLESS they are arguments
      to an API call or inside an object (so payloads survive).
    - ERROR nodes are traversed normally (MQL syntax causes these).

    Args:
        node        : Current tree-sitter Node.
        source_bytes: Original encoded source bytes.
        intervals   : Accumulator list of (start_byte, end_byte) tuples.
    """
    node_type = node.type

    if node_type in COMMENT_NODE_TYPES:
        intervals.append((node.start_byte, node.end_byte))
        return

    if node_type in STRING_NODE_TYPES:
        if _is_preserved_string(node, source_bytes):
            return  # keep — Payload data or MQL string lives here
        intervals.append((node.start_byte, node.end_byte))
        return

    for child in node.children:
        _collect_strip_intervals(child, source_bytes, intervals)


def _blank_intervals(source_bytes: bytes, intervals: list) -> str:
    """
    Replace byte ranges with spaces, keeping newlines intact.

    Newlines are preserved so that line numbers in downstream analysis
    remain aligned with the original source file.

    Args:
        source_bytes (bytes): Original encoded source.
        intervals    (list) : List of (start_byte, end_byte) int pairs.

    Returns:
        str: Cleaned source decoded as UTF-8.
    """
    buf = bytearray(source_bytes)
    for start, end in intervals:
        for i in range(start, end):
            if buf[i] != ord(b"\n"):
                buf[i] = ord(b" ")
    return buf.decode("utf-8", errors="replace")
