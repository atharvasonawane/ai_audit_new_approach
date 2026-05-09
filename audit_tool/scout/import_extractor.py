"""
scout/import_extractor.py
───────────────────────────────────────────────────────────────
Extracts component relationships using pre-compiled tree_sitter_languages.
"""

from audit_tool.utils.logger import get_logger

try:
    from tree_sitter_languages import get_parser
    js_parser = get_parser("javascript")
except Exception as e:
    js_parser = None

logger = get_logger(__name__)

def extract_imports(script_code: str) -> list[str]:
    imports = []
    if not script_code.strip() or js_parser is None:
        return imports

    try:
        source_bytes = script_code.encode("utf8")
        tree = js_parser.parse(source_bytes)

        def traverse(node):
            if node.type == "import_statement":
                for child in node.children:
                    if child.type == "string":
                        path = source_bytes[child.start_byte:child.end_byte].decode("utf8").strip("'\"")
                        if path.startswith("."):
                            imports.append(path)
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
    except Exception as e:
        logger.error(f"Error extracting imports via AST: {e}")

    return imports
