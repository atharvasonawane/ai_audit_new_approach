import re
import logging
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml

# tree-sitter imports with pack fallback
try:
    from tree_sitter import Language, Parser, Query, QueryCursor
    from tree_sitter_language_pack import get_language

    JS_LANGUAGE = get_language("javascript")
    _TS_AVAILABLE = True
except ImportError:
    _TS_AVAILABLE = False
    JS_LANGUAGE = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tree-Sitter Patterns (S-Expressions)
# ---------------------------------------------------------------------------

# 1. Fetch: Matches fetch(...)
FETCH_QUERY = (
    '(call_expression function: (identifier) @fn_name (#eq? @fn_name "fetch")) @call'
)

# 2. Axios: Matches axios(...)
AXIOS_BASE_QUERY = (
    '(call_expression function: (identifier) @fn_name (#eq? @fn_name "axios")) @call'
)

# 3. Axios Methods: Matches axios.get(...) etc.
AXIOS_METHOD_QUERY = '(call_expression function: (member_expression object: (identifier) @obj_name (#eq? @obj_name "axios"))) @call'

# 4. $http: Matches this.$http(...)
HTTP_BASE_QUERY = '(call_expression function: (member_expression object: (this) property: (property_identifier) @prop_name (#eq? @prop_name "$http"))) @call'

# 5. $http Methods: Matches this.$http.get(...)
HTTP_METHOD_QUERY = '(call_expression function: (member_expression object: (member_expression object: (this) property: (property_identifier) @prop_name (#eq? @prop_name "$http")))) @call'

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_api_calls(
    cleaned_script_text: str,
    raw_script_text: str,
    filepath: str,
    config_path: str,
) -> dict:
    """Extract all API calls (MQL and Generic) using a Hybrid Tree-Sitter + Regex approach."""
    cfg = _load_config(config_path)
    module = cfg.get("module", "unknown")

    mql_config = cfg.get("mql", {})
    mql_pattern_str = mql_config.get(
        "pattern", r'\.setActivity\s*\(\s*["\']([rso]\.\[([^\]]+)\])["\']\s*\)'
    )

    calls: List[Dict[str, Any]] = []

    # --- BLOCK DETECTION (Tree-Sitter Based) ---
    mounted_ranges = []
    loop_ranges = []

    if _TS_AVAILABLE and JS_LANGUAGE and raw_script_text:
        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(raw_script_text.encode("utf-8"))
        root = tree.root_node

        # Walk the tree for blocks
        def _walk_blocks(node):
            # Check for mounted/created
            # method_definition: mounted() {}
            # pair: mounted: function() {} or mounted: () => {}
            # function_declaration: function mounted() {} (unlikely in Vue but possible)
            prop_name = ""
            if node.type in ["method_definition", "pair", "function_declaration"]:
                key_node = node.child_by_field_name("name") or node.child_by_field_name(
                    "key"
                )
                if key_node:
                    prop_name = key_node.text.decode("utf-8")

                if prop_name in ["mounted", "created"]:
                    mounted_ranges.append((node.start_point[0], node.end_point[0]))

            # Check for loops
            if node.type in [
                "for_statement",
                "for_in_statement",
                "for_of_statement",
                "while_statement",
            ]:
                loop_ranges.append((node.start_point[0], node.end_point[0]))

            # Check for array methods (forEach, map, filter)
            if node.type == "call_expression":
                fn = node.child_by_field_name("function")
                if fn and fn.type == "member_expression":
                    prop = fn.child_by_field_name("property")
                    if prop and prop.text.decode("utf-8") in [
                        "forEach",
                        "map",
                        "filter",
                    ]:
                        loop_ranges.append((node.start_point[0], node.end_point[0]))

            for child in node.children:
                _walk_blocks(child)

        _walk_blocks(root)

        # --- GENERIC API EXTRACTION (Tree-Sitter Based) ---
        queries = [
            ("fetch", FETCH_QUERY),
            ("axios", AXIOS_BASE_QUERY),
            ("axios", AXIOS_METHOD_QUERY),
            ("$http", HTTP_BASE_QUERY),
            ("$http", HTTP_METHOD_QUERY),
        ]

        for name, q_str in queries:
            try:
                # In tree-sitter 0.25.x (this user's version),
                # QueryCursor.captures() returns a dict: {label: [nodes]}
                query = Query(JS_LANGUAGE, q_str)
                cursor = QueryCursor(query)
                captures = cursor.captures(root)

                if "call" in captures:
                    for node in captures["call"]:
                        line_idx = node.start_point[0]
                        full_text = node.text.decode("utf-8")
                        calls.append(
                            {
                                "type": "GENERIC",
                                "method": name,
                                "full_match": full_text.splitlines()[0][:100],
                                "in_mounted": any(
                                    s <= line_idx <= e for s, e in mounted_ranges
                                ),
                                "in_loop": any(
                                    s <= line_idx <= e for s, e in loop_ranges
                                ),
                                "line_number": line_idx + 1,
                            }
                        )
            except Exception as e:
                logger.warning(
                    "[api_extractor] Tree-Sitter query failed for %s: %s", name, e
                )

    # --- MQL EXTRACTION (Regex Based - Robust to non-standard syntax) ---
    clean_lines = cleaned_script_text.splitlines()
    mql_regex = re.compile(mql_pattern_str)

    for line_idx, line in enumerate(clean_lines):
        for match in mql_regex.finditer(line):
            # If groups exist, group 1 is usually the 'o.[Method]' part
            method_name = match.group(1) if match.groups() else match.group(0)
            calls.append(
                {
                    "type": "MQL",
                    "method": method_name,
                    "full_match": match.group(0),
                    "in_mounted": any(s <= line_idx <= e for s, e in mounted_ranges),
                    "in_loop": any(s <= line_idx <= e for s, e in loop_ranges),
                    "line_number": line_idx + 1,
                }
            )

    total_count = len(calls)
    mounted_count = sum(1 for c in calls if c["in_mounted"])
    name_counts = Counter(c["method"] for c in calls)
    duplicates = [name for name, cnt in name_counts.items() if cnt > 1]

    return {
        "file": filepath,
        "module": module,
        "calls": calls,
        "total_count": total_count,
        "mounted_count": mounted_count,
        "methods_with_same_name": duplicates,
    }


def _get_api_payload_nodes(cleaned_script: str) -> list:
    """Helper to find all object literals passed into API calls."""
    if not _TS_AVAILABLE or not JS_LANGUAGE or not cleaned_script:
        return []

    parser = Parser(JS_LANGUAGE)
    src_bytes = cleaned_script.encode("utf-8")
    tree = parser.parse(src_bytes)

    payload_nodes = []

    def walk(node):
        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                func_name = src_bytes[func_node.start_byte : func_node.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                if any(
                    api in func_name for api in ["fetch", "axios", "$http", "setData"]
                ):
                    args_node = node.child_by_field_name("arguments")
                    if args_node:
                        # Look for object literals { } within the arguments
                        for arg in args_node.children:
                            if arg.type == "object":
                                payload_nodes.append(arg)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return payload_nodes


def count_payload_keys(cleaned_script: str) -> int:
    """Count total keys across all API payloads."""
    payload_nodes = _get_api_payload_nodes(cleaned_script)
    total_keys = 0

    for payload in payload_nodes:

        def count_pairs(node):
            count = 1 if node.type == "pair" else 0
            for child in node.children:
                count += count_pairs(child)
            return count

        total_keys += count_pairs(payload)

    return total_keys


def calculate_payload_depth(cleaned_script: str) -> int:
    """Find the MAX nesting depth of any API payload."""
    payload_nodes = _get_api_payload_nodes(cleaned_script)
    if not payload_nodes:
        return 0

    def get_depth(node) -> int:
        if node.type == "object":
            depths = [0]
            for child in node.children:
                if child.type == "pair":
                    val = child.child_by_field_name("value")
                    if val and val.type == "object":
                        depths.append(get_depth(val))
            return 1 + max(depths)
        return 0

    return max((get_depth(payload) for payload in payload_nodes), default=0)


def calculate_payload_size_kb(cleaned_script: str) -> float:
    """Calculate the total size of all API payloads in KB."""
    payload_nodes = _get_api_payload_nodes(cleaned_script)
    total_bytes = 0

    for payload in payload_nodes:
        total_bytes += payload.end_byte - payload.start_byte

    return float(total_bytes) / 1024.0


def _empty_result(filepath: str, module: str) -> dict:
    return {
        "file": filepath,
        "module": module,
        "calls": [],
        "total_count": 0,
        "mounted_count": 0,
        "methods_with_same_name": [],
    }


if __name__ == "__main__":
    # Test block
    logging.basicConfig(level=logging.INFO)
    test_js = """
    export default {
        mounted() {
            fetch('/api/v1/users');
            this.load();
            [1,2].forEach(item => {
                 axios.get('/api/item/' + item);
            });
        },
        methods: {
            load() {
                new MQL().setActivity("o.[GetProfile]").fetch().then(r => {
                    this.$http.post('/log', {data: r});
                });
            }
        }
    }
    """
    res = extract_api_calls(test_js, test_js, "test.vue", "nonexistent.yaml")
    print(f"Total: {res['total_count']}, Mounted: {res['mounted_count']}")
    for c in res["calls"]:
        print(
            f"[{c['type']}] {c['method']} at L{c['line_number']} (mounted={c['in_mounted']}, loop={c['in_loop']})"
        )
