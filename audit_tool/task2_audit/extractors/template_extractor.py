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
                           (PascalCase) or contains a hyphen (kebab-case).
                           Counts DISTINCT names, not total occurrences.
        max_nesting_depth— walks the AST recursively, tracking the depth
                           counter each time we enter an element that has a
                           v-if or v-for attribute.

Dependencies:
    pip install tree-sitter tree-sitter-language-pack
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tags that are native HTML, not child components
_NATIVE_HTML_TAGS = {
    "a", "abbr", "address", "article", "aside", "audio",
    "b", "blockquote", "body", "br", "button", "canvas",
    "caption", "cite", "code", "col", "colgroup", "data",
    "datalist", "dd", "del", "details", "dfn", "dialog",
    "div", "dl", "dt", "em", "embed", "fieldset", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "head", "header", "hr", "html", "i", "iframe", "img", "input",
    "ins", "kbd", "label", "legend", "li", "link", "main",
    "map", "mark", "menu", "meta", "meter", "nav", "noscript",
    "object", "ol", "optgroup", "option", "output", "p", "picture",
    "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp",
    "script", "section", "select", "small", "source", "span",
    "strong", "style", "sub", "summary", "sup", "svg", "table",
    "tbody", "td", "template", "textarea", "tfoot", "th", "thead",
    "time", "title", "tr", "track", "u", "ul", "var", "video", "wbr",
    # Vue built-ins
    "transition", "transition-group", "keep-alive", "slot", "component",
    "router-view", "router-link", "suspense", "teleport",
}


def extract_template_metrics(
    template_node,
    source_bytes: bytes,
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
            child_components  (int): Distinct child component tag count.
            max_nesting_depth (int): Deepest v-if/v-for nesting level.
    """
    if template_node is None:
        logger.warning("[template_extractor] No template_node provided.")
        return {
            "template_lines":    0,
            "child_components":  0,
            "max_nesting_depth": 0,
        }

    # --- 1. template_lines ---
    template_text = source_bytes[
        template_node.start_byte : template_node.end_byte
    ].decode("utf-8", errors="replace")
    template_lines = template_text.count("\n") + 1

    # --- 2. child_components and 3. max_nesting_depth ---
    component_tags: set = set()
    max_depth = _walk_template(template_node, source_bytes, component_tags, 0, is_root=True)

    logger.debug(
        "[template_extractor] lines=%d, components=%d, max_depth=%d",
        template_lines, len(component_tags), max_depth
    )

    return {
        "template_lines":    template_lines,
        "child_components":  len(component_tags),
        "max_nesting_depth": max_depth,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_component_tag(tag_name: str) -> bool:
    """
    Return True if the tag name looks like a Vue component (not native HTML).

    Rules:
        - Starts with uppercase              -> PascalCase component
        - Contains a hyphen and not in native -> kebab-case component
        - Otherwise -> native HTML element
    """
    if not tag_name:
        return False
    if tag_name[0].isupper():
        return True
    if "-" in tag_name and tag_name.lower() not in _NATIVE_HTML_TAGS:
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
                            name = source_bytes[sub.start_byte:sub.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                            if name.startswith(prefix):
                                return True
                elif attr.type == "directive_attribute":
                    for sub in attr.children:
                        if sub.type in ("directive_name", "directive_short_hand"):
                            name = source_bytes[sub.start_byte:sub.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                            if name.startswith(prefix) or (prefix == "v-on" and name.startswith("@")) or (prefix == "v-bind" and name.startswith(":")):
                                return True
    return False


def _get_tag_name(element_node, source_bytes: bytes) -> str:
    """Extract the tag name string from an element or self_closing_tag node."""
    for child in element_node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for sub in child.children:
                if sub.type == "tag_name":
                    return source_bytes[sub.start_byte:sub.end_byte].decode(
                        "utf-8", errors="replace"
                    ).strip()
    return ""


def _walk_template(
    node,
    source_bytes: bytes,
    component_tags: set,
    current_depth: int,
    is_root: bool = False
) -> int:
    """
    Recursively walk the template AST.

    - Collects distinct component tag names into `component_tags`.
    - Tracks absolute HTML DOM nesting depth (Copilot definition).
    - Returns the maximum depth seen in this subtree.

    Args:
        node           : Current tree-sitter Node.
        source_bytes   : Source bytes for text extraction.
        component_tags : Mutable set — component names are added here.
        current_depth  : Current nesting depth level.
        is_root        : True if this is the top-level <template> tag.

    Returns:
        int: Maximum HTML nesting depth seen at or below this node.
    """
    max_seen = current_depth

    if node.type in ("element", "self_closing_element"):
        tag = _get_tag_name(node, source_bytes)

        # Collect component tag names (once per distinct name)
        if tag and _is_component_tag(tag):
            component_tags.add(tag)

        # The root <template> node itself is Depth 0.
        # Everything inside it increases depth by 1.
        child_depth = current_depth if is_root else current_depth + 1
    else:
        child_depth = current_depth

    for child in node.children:
        child_max = _walk_template(child, source_bytes, component_tags, child_depth)
        if child_max > max_seen:
            max_seen = child_max

    return max_seen


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

    with open(SAMPLE_PATH, "rb") as f:
        source_bytes = f.read()

    parsed = parse_vue_file(SAMPLE_PATH)
    tmpl   = parsed.get("template_node")

    result = extract_template_metrics(tmpl, source_bytes)

    out = []
    out.append("=== template_extractor.py self-test ===")
    out.append(f"File  : {SAMPLE_PATH}")
    out.append(f"template_lines    : {result['template_lines']}")
    out.append(f"child_components  : {result['child_components']}")
    out.append(f"max_nesting_depth : {result['max_nesting_depth']}")

    for line in out:
        print(line)

    Path(BASE / "_template_results.txt").write_text(
        "\n".join(out), encoding="utf-8"
    )
    print("Saved to _template_results.txt")
