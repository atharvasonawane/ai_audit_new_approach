"""
extractors/template_extractor.py
=================================
Role in pipeline (feeds into flag_engine.py):
    Analyses the <template> AST node produced by vue_parser.py and counts
    the three metrics that flag_engine needs for template/UI flag evaluation:

        template_lines   (int) : line count of the <template> block
        child_components (int) : distinct PascalCase or kebab-case component tags
        max_nesting_depth(int) : deepest v-if / v-for nesting level

    HOW EACH IS COUNTED:
        template_lines   — counted from the node's start/end position in
                           the source bytes (no regex needed).
        child_components — walks the AST for element nodes; a tag is
                           a component if it starts with an uppercase letter
                   (PascalCase), contains uppercase letters (camelCase),
                   or contains a hyphen (kebab-case).
                   Counts TOTAL occurrences, not distinct names.
        max_nesting_depth— walks the AST recursively, tracking the depth
                           counter each time we enter an element that has a
                           v-if or v-for attribute.

Dependencies:
    pip install tree-sitter tree-sitter-language-pack
"""

import re
import logging

try:
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language

    _JS_LANGUAGE = get_language("javascript")
    _TS_AVAILABLE = True
except ImportError:
    _JS_LANGUAGE = None
    _TS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Tags that are native HTML, not child components
_NATIVE_HTML_TAGS = {
    "a",
    "abbr",
    "address",
    "article",
    "aside",
    "audio",
    "b",
    "blockquote",
    "body",
    "br",
    "button",
    "canvas",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "data",
    "datalist",
    "dd",
    "del",
    "details",
    "dfn",
    "dialog",
    "div",
    "dl",
    "dt",
    "em",
    "embed",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hr",
    "html",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "legend",
    "li",
    "link",
    "main",
    "map",
    "mark",
    "menu",
    "meta",
    "meter",
    "nav",
    "noscript",
    "object",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "picture",
    "pre",
    "progress",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "script",
    "section",
    "select",
    "small",
    "source",
    "span",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "svg",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "track",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
    # Vue built-ins
    "transition",
    "transition-group",
    "keep-alive",
    "slot",
    "component",
    "router-view",
    "router-link",
    "suspense",
    "teleport",
}


def extract_template_metrics(
    template_node,
    source_bytes: bytes,
    script_text: str = "",
) -> dict:
    """
    Analyse the <template> AST node and return the three metrics needed
    by flag_engine.evaluate_flags().

    Args:
        template_node : The tree-sitter Node for the <template> element,
                        as returned in parse_vue_file()["template_node"].
                        Pass None if the component has no template block.
        source_bytes  : The full .vue file content as bytes, used to
                        compute line numbers from byte offsets.

    Returns:
        dict with keys:
            template_lines    (int): Number of lines in the template block.
            child_components  (int): Total child component tag occurrences.
            max_nesting_depth (int): Deepest v-if/v-for nesting level.
    """
    if template_node is None:
        logger.warning("[template_extractor] No template_node provided.")
        return {
            "template_lines": 0,
            "child_components": 0,
            "max_nesting_depth": 0,
        }

    # --- 1. template_lines ---
    source_text = source_bytes.decode("utf-8", errors="replace")
    template_lines = _count_template_lines(source_text)
    if template_lines == 0:
        # Fallback to AST points if raw tag matching fails
        template_lines = max(
            0, template_node.end_point[0] - template_node.start_point[0] - 1
        )

    registered_components = _extract_registered_components(script_text)

    # --- 2. child_components and 3. max_nesting_depth ---
    component_tags = set()
    max_depth = _walk_template(
        template_node,
        source_bytes,
        registered_components,
        component_tags,
        0,
        is_root=True,
    )

    logger.debug(
        "[template_extractor] lines=%d, components=%d, max_depth=%d",
        template_lines,
        len(component_tags),
        max_depth,
    )

    return {
        "template_lines": template_lines,
        "child_components": len(component_tags),
        "max_nesting_depth": max_depth,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_component_tag(tag_name: str, registered_components: set) -> bool:
    """
    Return True if the tag name looks like a Vue component (not native HTML).

    Rules:
        - Native HTML/Vue built-ins and slot wrappers are not components
        - PrimeVue table internals like Column/ColumnGroup/Row are excluded
        - Registered components are components regardless of casing
        - Unregistered tags count only when PascalCase
    """
    if not tag_name:
        return False
    lowered = tag_name.lower()
    if lowered in _NATIVE_HTML_TAGS:
        return False

    # Exclude common PrimeVue table internals that heavily inflate counts
    if lowered in {"column", "columngroup", "row"}:
        return False

    if tag_name in registered_components or lowered in registered_components:
        return True

    # For unregistered tags, only PascalCase qualifies.
    if re.match(r"^[A-Z][A-Za-z0-9]*$", tag_name):
        return True
    return False


def _has_directive(element_node, source_bytes: bytes, prefix: str) -> bool:
    """
    Return True if the element node has an attribute starting with `prefix`.

    Checks the element's start_tag child for attribute nodes whose name
    starts with the given prefix (e.g. 'v-if', 'v-for').
    """
    for child in element_node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for attr in child.children:
                if attr.type == "attribute":
                    for sub in attr.children:
                        if sub.type == "attribute_name":
                            name = source_bytes[sub.start_byte : sub.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                            if name.startswith(prefix):
                                return True
                elif attr.type == "directive_attribute":
                    for sub in attr.children:
                        if sub.type in ("directive_name", "directive_short_hand"):
                            name = source_bytes[sub.start_byte : sub.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                            if (
                                name.startswith(prefix)
                                or (prefix == "v-on" and name.startswith("@"))
                                or (prefix == "v-bind" and name.startswith(":"))
                            ):
                                return True
    return False


def _get_tag_name(element_node, source_bytes: bytes) -> str:
    """Extract the tag name string from an element or self_closing_tag node."""
    for child in element_node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for sub in child.children:
                if sub.type == "tag_name":
                    return (
                        source_bytes[sub.start_byte : sub.end_byte]
                        .decode("utf-8", errors="replace")
                        .strip()
                    )
    return ""


def _walk_template(
    node,
    source_bytes: bytes,
    registered_components: set,
    component_tags: set,
    current_depth: int,
    is_root: bool = False,
) -> int:
    """
    Recursively walk the template AST.

    - Collects distinct component tags into `component_tags`.
    - Tracks absolute HTML DOM nesting depth (Copilot definition).
    - Returns the maximum depth seen in this subtree.

    Args:
        node           : Current tree-sitter Node.
        source_bytes   : Source bytes for text extraction.
        registered_components: set — names from components: { ... } in script.
        component_tags: set — distinct component names used in template.
        current_depth  : Current nesting depth level.
        is_root        : True if this is the top-level <template> tag.

    Returns:
        int: Maximum HTML nesting depth seen at or below this node.
    """
    max_seen = current_depth

    if node.type in ("element", "self_closing_element"):
        tag = _get_tag_name(node, source_bytes)

        if tag and _is_component_tag(tag, registered_components):
            component_tags.add(tag)

        # The root <template> node itself is Depth 0.
        # Everything inside it increases depth by 1.
        child_depth = current_depth if is_root else current_depth + 1
    else:
        child_depth = current_depth

    for child in node.children:
        child_max = _walk_template(
            child, source_bytes, registered_components, component_tags, child_depth
        )
        if child_max > max_seen:
            max_seen = child_max

    return max_seen


def _count_template_lines(source_text: str) -> int:
    """Count lines from <template>...</template> inclusive, then subtract 2 tags."""
    open_re = re.compile(r"<template\b[^>]*>", re.IGNORECASE)
    close_re = re.compile(r"</template>", re.IGNORECASE)

    open_match = open_re.search(source_text)
    if not open_match:
        return 0

    start_idx = open_match.start()
    end_match = None
    for token in close_re.finditer(source_text, pos=start_idx):
        end_match = token

    if end_match is None:
        return 0
    end_idx = end_match.end()

    inclusive_lines = source_text[start_idx:end_idx].count("\n") + 1
    return max(0, inclusive_lines - 2)


def _extract_registered_components(script_text: str) -> set:
    """Extract component keys from the top-level components: { ... } block."""
    if not script_text:
        return set()

    ast_names = _extract_registered_components_ast(script_text)
    if ast_names:
        return ast_names

    match = re.search(r"\bcomponents\s*:\s*\{", script_text)
    if not match:
        return set()

    open_brace = script_text.find("{", match.start())
    if open_brace < 0:
        return set()

    end_idx = _find_matching_brace(script_text, open_brace)

    if end_idx < 0:
        return set()

    block = script_text[open_brace + 1 : end_idx]
    names = set()
    block_depth = 0
    chunk_start = 0

    for i, ch in enumerate(block):
        if ch == "{":
            block_depth += 1
        elif ch == "}":
            block_depth -= 1
        elif ch == "," and block_depth == 0:
            _register_component_name(block[chunk_start:i], names)
            chunk_start = i + 1

    _register_component_name(block[chunk_start:], names)
    return names


def _register_component_name(segment: str, names: set) -> None:
    text = segment.strip()
    if not text:
        return

    key_match = re.match(r"^['\"]?([A-Za-z][A-Za-z0-9_-]*)['\"]?\s*:", text)
    if key_match:
        key = key_match.group(1)
        names.add(key)
        names.add(key.lower())
        return

    shorthand_match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)$", text)
    if shorthand_match:
        key = shorthand_match.group(1)
        names.add(key)
        names.add(key.lower())


def _extract_registered_components_ast(script_text: str) -> set:
    if not _TS_AVAILABLE or _JS_LANGUAGE is None:
        return set()

    try:
        parser = Parser(_JS_LANGUAGE)
        tree = parser.parse(script_text.encode("utf-8", errors="replace"))
    except Exception:
        return set()

    source_bytes = script_text.encode("utf-8", errors="replace")
    names = set()

    def node_text(node):
        return source_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

    def walk(node):
        if node.type == "pair":
            key_node = node.child_by_field_name("key")
            val_node = node.child_by_field_name("value")
            if key_node and val_node:
                key = node_text(key_node).strip("'\"")
                if key == "components" and val_node.type == "object":
                    for child in val_node.children:
                        if child.type in (
                            "pair",
                            "method_definition",
                            "shorthand_property_identifier",
                        ):
                            ckey = ""
                            if child.type == "pair":
                                ckey_node = child.child_by_field_name("key")
                                if ckey_node:
                                    ckey = node_text(ckey_node).strip("'\"")
                            elif child.type == "method_definition":
                                ckey_node = child.child_by_field_name("name")
                                if ckey_node:
                                    ckey = node_text(ckey_node).strip("'\"")
                            elif child.type == "shorthand_property_identifier":
                                ckey = node_text(child).strip("'\"")

                            if ckey:
                                names.add(ckey)
                                names.add(ckey.lower())
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return names


def _find_matching_brace(text: str, open_brace_idx: int) -> int:
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

    with open(SAMPLE_PATH, "rb") as f:
        source_bytes = f.read()

    parsed = parse_vue_file(SAMPLE_PATH)
    tmpl = parsed.get("template_node")

    result = extract_template_metrics(tmpl, source_bytes)

    out = []
    out.append("=== template_extractor.py self-test ===")
    out.append(f"File  : {SAMPLE_PATH}")
    out.append(f"template_lines    : {result['template_lines']}")
    out.append(f"child_components  : {result['child_components']}")
    out.append(f"max_nesting_depth : {result['max_nesting_depth']}")

    for line in out:
        print(line)

    Path(BASE / "_template_results.txt").write_text("\n".join(out), encoding="utf-8")
    print("Saved to _template_results.txt")
