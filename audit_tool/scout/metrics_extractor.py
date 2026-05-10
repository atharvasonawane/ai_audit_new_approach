"""
scout/metrics_extractor.py
───────────────────────────────────────────────────────────────
Extracts structural metrics using pre-compiled tree_sitter_languages.
"""

import re
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
    """
    Parse JS/TS using tree-sitter. Prefer the TypeScript parser because it
    tolerates type annotations and TS syntax used in enterprise Vue codebases.
    """
    parser = ts_parser or js_parser
    if parser is None:
        return None
    return parser.parse(source_bytes)


def _node_text(node, source_bytes: bytes) -> str | None:
    if node is None:
        return None
    if node.type in {"property_identifier", "identifier", "shorthand_property_identifier"}:
        return source_bytes[node.start_byte:node.end_byte].decode("utf8", errors="replace")
    if node.type == "string":
        raw = source_bytes[node.start_byte:node.end_byte].decode("utf8", errors="replace")
        return raw.strip("'\"")
    return None

def extract_template_metrics(template_code: str) -> dict:
    metrics = {"max_nesting_depth": 0}
    if not template_code.strip():
        return metrics

    depth = 0
    max_depth = 0
    tags = re.findall(r'<(\/?[a-zA-Z0-9\-]+)[^>]*>', template_code)
    self_closing = {"img", "br", "hr", "input", "meta", "link", "col"}
    for tag in tags:
        if tag.startswith('/'):
            depth = max(0, depth - 1)
        else:
            if tag.lower() not in self_closing:
                depth += 1
                max_depth = max(max_depth, depth)
    metrics["max_nesting_depth"] = max_depth
    return metrics


def extract_script_metrics(script_code: str) -> dict:
    metrics = {
        "methods": 0, "computed": 0, "watchers": 0,
        "props": 0, "emits": 0, "cyclomatic_complexity": 0,
    }

    if not script_code.strip() or (ts_parser is None and js_parser is None):
        return metrics

    try:
        source_bytes = script_code.encode("utf8")
        tree = _parse_script(source_bytes)
        if tree is None:
            return metrics
        
        complexity_nodes = {
            "if_statement", "for_statement", "for_in_statement", 
            "for_of_statement", "while_statement", "do_statement", "ternary_expression",
            "switch_statement",
        }

        def traverse(node):
            if node.type in complexity_nodes:
                metrics["cyclomatic_complexity"] += 1
            elif node.type == "binary_expression":
                operator = ""
                for child in node.children:
                    if child.type in {"&&", "||"}:
                        operator = child.type
                        break
                if operator:
                    metrics["cyclomatic_complexity"] += 1

            if node.type == "call_expression" and node.children:
                func_name = _node_text(node.children[0], source_bytes) or ""
                
                if func_name == "computed":
                    metrics["computed"] += 1
                elif func_name == "watch":
                    metrics["watchers"] += 1
                elif func_name == "defineProps":
                    metrics["props"] += 1
                elif func_name == "defineEmits":
                    metrics["emits"] += 1

            if node.type == "variable_declarator":
                has_func = any(c.type in {"arrow_function", "function"} for c in node.children)
                if has_func:
                    metrics["methods"] += 1

            if node.type == "pair" and node.children:
                key_name = _node_text(node.children[0], source_bytes)
                if key_name == "methods":
                    val = node.children[-1]
                    if val.type == "object":
                        metrics["methods"] += sum(1 for c in val.children if c.type in {"pair", "method_definition"})
                elif key_name == "computed":
                    val = node.children[-1]
                    if val.type == "object":
                        metrics["computed"] += sum(1 for c in val.children if c.type in {"pair", "method_definition"})
                elif key_name == "watch":
                    val = node.children[-1]
                    if val.type == "object":
                        metrics["watchers"] += sum(1 for c in val.children if c.type in {"pair", "method_definition"})
                elif key_name == "props":
                    val = node.children[-1]
                    if val.type == "object":
                        metrics["props"] += sum(1 for c in val.children if c.type == "pair")
                    elif val.type == "array":
                        metrics["props"] += sum(1 for c in val.children if c.type == "string")
                elif key_name == "emits":
                    val = node.children[-1]
                    if val.type == "array":
                        metrics["emits"] += sum(1 for c in val.children if c.type == "string")
                    elif val.type == "object":
                        metrics["emits"] += sum(1 for c in val.children if c.type == "pair")

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        metrics["cyclomatic_complexity"] += 1

    except Exception as e:
        logger.error("Error extracting script metrics: %s", e)

    return metrics
