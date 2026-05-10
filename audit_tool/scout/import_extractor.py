"""
scout/import_extractor.py
───────────────────────────────────────────────────────────────
Extracts component relationships using pre-compiled tree_sitter_languages.
"""

from audit_tool.utils.logger import get_logger

try:
    from tree_sitter_languages import get_parser
    ts_parser = get_parser("typescript")
    js_parser = get_parser("javascript")
except Exception as e:
    ts_parser = None
    js_parser = None

logger = get_logger(__name__)


def _parse_script(source_bytes: bytes):
    parser = ts_parser or js_parser
    if parser is None:
        return None
    return parser.parse(source_bytes)


def extract_imports(script_code: str) -> list[str]:
    imports = []
    if not script_code.strip() or (ts_parser is None and js_parser is None):
        return imports

    try:
        source_bytes = script_code.encode("utf8")
        tree = _parse_script(source_bytes)
        if tree is None:
            return imports

        def traverse(node):
            if node.type == "import_statement":
                for child in node.children:
                    if child.type == "string":
                        path = source_bytes[child.start_byte:child.end_byte].decode("utf8").strip("'\"")
                        if path.startswith("."):
                            imports.append(path)
            # CommonJS: require("./foo")
            elif node.type == "call_expression" and node.children:
                callee = node.children[0]
                if callee.type == "identifier":
                    name = source_bytes[callee.start_byte:callee.end_byte].decode("utf8", errors="replace")
                    if name == "require" and len(node.children) > 1:
                        args = node.children[1]
                        if args.type == "arguments":
                            for arg in args.children:
                                if arg.type == "string":
                                    path = source_bytes[arg.start_byte:arg.end_byte].decode("utf8").strip("'\"")
                                    if path.startswith("."):
                                        imports.append(path)
                                    break
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
    except Exception as e:
        logger.error("Error extracting imports via AST: %s", e)

    return imports
