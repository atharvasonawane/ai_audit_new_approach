"""
scout/api_extractor.py
───────────────────────────────────────────────────────────────
Extracts API calls using pre-compiled tree_sitter_languages.
"""

from audit_tool.utils.logger import get_logger

try:
    from tree_sitter_languages import get_parser
    js_parser = get_parser("javascript")
except Exception as e:
    js_parser = None

logger = get_logger(__name__)

API_CLIENTS = {"axios", "fetch", "$http"}
LIFECYCLE_HOOKS = {"onMounted", "mounted"}
LOOP_NODES = {"for_statement", "for_in_statement", "while_statement", "do_statement"}

def extract_api_calls(script_code: str, line_offset: int = 0) -> list[dict]:
    calls = []
    if not script_code.strip() or js_parser is None:
        return calls

    try:
        source_bytes = script_code.encode("utf8")
        tree = js_parser.parse(source_bytes)

        def traverse(node, ancestors):
            if node.type == "call_expression":
                func_node = node.children[0]
                
                api_type = None
                method_name = "unknown"
                
                if func_node.type == "identifier":
                    name = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf8")
                    if name in API_CLIENTS:
                        api_type = name
                        method_name = name
                elif func_node.type == "member_expression":
                    obj_node = func_node.children[0]
                    prop_node = func_node.children[2] if len(func_node.children) > 2 else None
                    if obj_node.type == "identifier":
                        obj_name = source_bytes[obj_node.start_byte:obj_node.end_byte].decode("utf8")
                        if obj_name in API_CLIENTS:
                            api_type = obj_name
                            if prop_node and prop_node.type == "property_identifier":
                                method_name = source_bytes[prop_node.start_byte:prop_node.end_byte].decode("utf8")
                
                if api_type:
                    in_loop = any(a.type in LOOP_NODES for a in ancestors)
                    in_mounted = False
                    for a in ancestors:
                        if a.type == "call_expression":
                            if a.children[0].type == "identifier":
                                a_name = source_bytes[a.children[0].start_byte:a.children[0].end_byte].decode("utf8")
                                if a_name in LIFECYCLE_HOOKS:
                                    in_mounted = True
                                    break
                        elif a.type == "method_definition" or a.type == "pair":
                            first_child = a.children[0]
                            if first_child.type == "property_identifier":
                                prop_name = source_bytes[first_child.start_byte:first_child.end_byte].decode("utf8")
                                if prop_name in LIFECYCLE_HOOKS:
                                    in_mounted = True
                                    break

                    endpoint = "unknown"
                    if len(node.children) > 1 and node.children[1].type == "arguments":
                        args_node = node.children[1]
                        for arg in args_node.children:
                            if arg.type == "string":
                                endpoint = source_bytes[arg.start_byte:arg.end_byte].decode("utf8").strip("'\"")
                                break

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
        logger.error(f"Error extracting API calls via AST: {e}")

    return calls
