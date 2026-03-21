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
COMMENT_NODE_TYPES: frozenset = frozenset({
    "comment",          # // single-line  and  /* multi-line */
})

STRING_NODE_TYPES: frozenset = frozenset({
    "string",           # 'single' and "double" quoted literals
    "template_string",  # `backtick template literals`
})

STRIP_NODE_TYPES: frozenset = COMMENT_NODE_TYPES | STRING_NODE_TYPES

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
        tree   = parser.parse(source_bytes)
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
        len(intervals), len(raw_script_text), len(cleaned),
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

def _is_setactivity_string_arg(node, source_bytes: bytes) -> bool:
    """
    Return True if this string node is the direct argument to .setActivity().

    In the Digital University codebase, MQL method names appear as:
        new MQL().setActivity('o.[LoginCopy]')

    tree-sitter AST shape:
        call_expression
          member_expression
            property_identifier  = "setActivity"   <- function being called
          arguments
            string  'o.[LoginCopy]'                <- this is the node to keep

    Checks:
        1. node.parent is  arguments
        2. node.parent.parent is  call_expression
        3. The call_expression's function child is a member_expression
           whose property_identifier text == "setActivity"

    Args:
        node        : A tree-sitter string node.
        source_bytes: Original source bytes (to read identifier names).

    Returns:
        bool: True if this string should be preserved.
    """
    parent = node.parent
    if parent is None or parent.type != "arguments":
        return False

    grandparent = parent.parent
    if grandparent is None or grandparent.type != "call_expression":
        return False

    # Find the function node of the call_expression
    function_node = grandparent.child_by_field_name("function")
    if function_node is None:
        for child in grandparent.children:
            if child.type in ("member_expression", "identifier"):
                function_node = child
                break

    if function_node is None or function_node.type != "member_expression":
        return False

    # Check property_identifier == "setActivity"
    for child in function_node.children:
        if child.type == "property_identifier":
            prop_name = source_bytes[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace"
            )
            if prop_name == "setActivity":
                return True

    return False


def _collect_strip_intervals(node, source_bytes: bytes, intervals: list) -> None:
    """
    Recursively walk the AST and record byte ranges to blank.

    - Comments are always stripped.
    - String/template literals are stripped UNLESS they are arguments
      to a .setActivity() call (where MQL method names live).
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
        if _is_setactivity_string_arg(node, source_bytes):
            logger.debug(
                "[script_cleaner] Preserving setActivity arg: %s",
                source_bytes[node.start_byte:node.end_byte][:60],
            )
            return  # keep — MQL name lives here
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
