"""
scout/api_extractor.py
───────────────────────────────────────────────────────────────
Extracts API calls using pre-compiled tree_sitter_languages.
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

API_CLIENTS = {"axios", "fetch", "$http", "$axios", "this.$http", "this.$axios"}
HTTP_METHOD_NAMES = {"get", "post", "put", "patch", "delete", "request", "head", "options"}
LIFECYCLE_HOOKS = {"onMounted", "mounted", "created", "beforeMount"}
LOOP_NODES = {"for_statement", "for_in_statement", "for_of_statement", "while_statement", "do_statement"}
ARRAY_LOOP_METHODS = {"forEach", "map", "filter", "reduce", "some", "every", "flatMap"}


def _parse_script(source_bytes: bytes):
    parser = ts_parser or js_parser
    if parser is None:
        return None
    return parser.parse(source_bytes)


def _node_text(node, source_bytes: bytes) -> str | None:
    if node is None:
        return None
    if node.type in {"identifier", "property_identifier", "shorthand_property_identifier"}:
        return source_bytes[node.start_byte:node.end_byte].decode("utf8", errors="replace")
    if node.type == "string":
        raw = source_bytes[node.start_byte:node.end_byte].decode("utf8", errors="replace")
        return raw.strip("'\"")
    return None


def _member_chain(node, source_bytes: bytes) -> list[str]:
    """
    Build a best-effort chain for nested member_expression nodes, e.g.
      this.$http.get  -> ["this", "$http", "get"]
      axios.post      -> ["axios", "post"]
    """
    if node is None:
        return []
    if node.type == "member_expression" and node.children:
        obj = node.children[0]
        prop = node.children[2] if len(node.children) > 2 else None
        chain = _member_chain(obj, source_bytes)
        prop_name = _node_text(prop, source_bytes)
        if prop_name:
            chain.append(prop_name)
        return chain
    text = _node_text(node, source_bytes)
    return [text] if text else []


def _extract_endpoint_from_arguments(args_node, source_bytes: bytes) -> str:
    # Heuristic: first string literal, otherwise { url: "..." }.
    if args_node is None or args_node.type != "arguments":
        return "unknown"

    for arg in args_node.children:
        if arg.type == "string":
            return source_bytes[arg.start_byte:arg.end_byte].decode("utf8", errors="replace").strip("'\"")
        if arg.type == "template_string":
            return "template_string"

    for arg in args_node.children:
        if arg.type == "object":
            for child in arg.children:
                if child.type != "pair" or not child.children:
                    continue
                key = _node_text(child.children[0], source_bytes)
                if key != "url":
                    continue
                value = child.children[-1]
                if value.type == "string":
                    return source_bytes[value.start_byte:value.end_byte].decode("utf8", errors="replace").strip("'\"")
                if value.type == "template_string":
                    return "template_string"
    return "unknown"

def extract_api_calls(script_code: str, line_offset: int = 0) -> list[dict]:
    calls = []
    if not script_code.strip() or (ts_parser is None and js_parser is None):
        return calls

    try:
        source_bytes = script_code.encode("utf8")
        tree = _parse_script(source_bytes)
        if tree is None:
            return calls

        def traverse(node, ancestors):
            if node.type == "call_expression":
                func_node = node.children[0]
                
                api_type = None
                method_name = "unknown"
                
                if func_node.type == "identifier":
                    name = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf8", errors="replace")
                    if name in API_CLIENTS:
                        api_type = name
                        method_name = name
                elif func_node.type == "member_expression":
                    chain = _member_chain(func_node, source_bytes)
                    # Detect common API clients in the chain (axios, $http, this.$http, etc.)
                    for idx, seg in enumerate(chain):
                        if seg in {"axios", "$http", "$axios"}:
                            api_type = seg
                            method_name = chain[-1] if chain else "unknown"
                            break
                        if idx + 1 < len(chain) and f"{seg}.{chain[idx + 1]}" in {"this.$http", "this.$axios"}:
                            api_type = f"{seg}.{chain[idx + 1]}"
                            method_name = chain[-1] if chain else "unknown"
                            break

                    # If the chain looks like an HTTP client method call, keep it.
                    if api_type and method_name not in HTTP_METHOD_NAMES and method_name != "fetch":
                        # Still keep it, but prefer marking the method name.
                        pass
                
                if api_type:
                    in_loop = any(a.type in LOOP_NODES for a in ancestors)
                    # Treat array iterator callbacks as "loop-like"
                    for a in ancestors:
                        if a.type != "call_expression" or not a.children:
                            continue
                        callee = a.children[0]
                        if callee.type == "member_expression":
                            chain = _member_chain(callee, source_bytes)
                            if chain and chain[-1] in ARRAY_LOOP_METHODS:
                                in_loop = True
                                break
                    in_mounted = False
                    for a in ancestors:
                        if a.type == "call_expression":
                            if a.children[0].type == "identifier":
                                a_name = source_bytes[a.children[0].start_byte:a.children[0].end_byte].decode("utf8", errors="replace")
                                if a_name in LIFECYCLE_HOOKS:
                                    in_mounted = True
                                    break
                        elif a.type == "method_definition" or a.type == "pair":
                            first_child = a.children[0]
                            if first_child.type == "property_identifier":
                                prop_name = source_bytes[first_child.start_byte:first_child.end_byte].decode("utf8", errors="replace")
                                if prop_name in LIFECYCLE_HOOKS:
                                    in_mounted = True
                                    break

                    endpoint = "unknown"
                    if len(node.children) > 1 and node.children[1].type == "arguments":
                        endpoint = _extract_endpoint_from_arguments(node.children[1], source_bytes)

                    calls.append({
                        "api_type": api_type,
                        "method_name": method_name,
                        "endpoint": endpoint,
                        "in_loop": in_loop,
                        "in_mounted": in_mounted,
                        "line_number": node.start_point[0] + 1 + line_offset
                    })

            new_ancestors = ancestors + [node]
            for child in node.children:
                traverse(child, new_ancestors)

        traverse(tree.root_node, [])
    except Exception as e:
        logger.error("Error extracting API calls via AST: %s", e)

    return calls
