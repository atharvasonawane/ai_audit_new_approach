import re
import logging
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

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

# API regexes (one API call per full request-chain invocation)
_AXIOS_CALL_RE = re.compile(
    r"\baxios\s*\.\s*(get|post|put|delete|request)\s*\(", re.IGNORECASE
)
_MQL_NEW_RE = re.compile(r"\bnew\s+MQL\s*\(", re.IGNORECASE)
_MQL_FETCH_RE = re.compile(r"\.fetch\s*\(", re.IGNORECASE)
_PROMISE_HANDLER_RE = re.compile(r"\.(then|catch|finally)\s*\(", re.IGNORECASE)
_MQL_ACTIVITY_RE = re.compile(
    r"\.setActivity\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE
)

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
    script_start_line: int = 1,
) -> dict:
    """Extract API calls with one count per request chain (MQL fetch + axios methods)."""
    cfg = _load_config(config_path)
    module = cfg.get("module", "unknown")

    calls: List[Dict[str, Any]] = []

    script_for_scan = cleaned_script_text if cleaned_script_text else raw_script_text
    if not script_for_scan:
        script_for_scan = ""
    mounted_ranges = _find_mounted_ranges(script_for_scan)
    promise_callback_ranges = _find_promise_callback_ranges(script_for_scan)

    # axios.get|post|put|delete|request(...) is one API call each.
    for match in _AXIOS_CALL_RE.finditer(script_for_scan):
        call_line = _line_number_for_index(script_for_scan, match.start())
        if _is_in_line_ranges(call_line, promise_callback_ranges):
            continue
        in_mounted = _is_in_line_ranges(call_line, mounted_ranges)
        calls.append(
            {
                "type": "AXIOS",
                "method": f"axios.{match.group(1).lower()}",
                "full_match": match.group(0),
                "in_mounted": in_mounted,
                "in_loop": False,
                "line_number": call_line + script_start_line - 1,
            }
        )

    # MQL chain: count one request per new MQL() chain that reaches .fetch().
    mql_starts = [m.start() for m in _MQL_NEW_RE.finditer(script_for_scan)]
    for idx, chain_start in enumerate(mql_starts):
        chain_end = (
            mql_starts[idx + 1] if idx + 1 < len(mql_starts) else len(script_for_scan)
        )
        chain_text = script_for_scan[chain_start:chain_end]

        fetch_match = _MQL_FETCH_RE.search(chain_text)
        if not fetch_match:
            continue

        fetch_abs_idx = chain_start + fetch_match.start()
        call_line = _line_number_for_index(script_for_scan, fetch_abs_idx)
        if _is_in_line_ranges(call_line, promise_callback_ranges):
            continue

        activity_match = _MQL_ACTIVITY_RE.search(chain_text)
        method_name = activity_match.group(1) if activity_match else "mql.fetch"
        in_mounted = _is_in_line_ranges(call_line, mounted_ranges)
        calls.append(
            {
                "type": "MQL",
                "method": method_name,
                "full_match": fetch_match.group(0),
                "in_mounted": in_mounted,
                "in_loop": False,
                "line_number": call_line + script_start_line - 1,
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


def _line_number_for_index(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _is_in_line_ranges(line_number: int, ranges: List[tuple]) -> bool:
    for start, end in ranges:
        if start <= line_number <= end:
            return True
    return False


def _extract_braced_block(text: str, open_brace_idx: int) -> tuple:
    depth = 0
    end_idx = -1
    for i in range(open_brace_idx, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx < 0:
        return ("", -1)
    return (text[open_brace_idx : end_idx + 1], end_idx)


def _find_mounted_ranges(script_text: str) -> List[tuple]:
    ranges: List[tuple] = []
    patterns = [
        re.compile(r"\bmounted\s*\([^)]*\)\s*\{"),
        re.compile(r"\bmounted\s*:\s*function\s*\([^)]*\)\s*\{"),
        re.compile(r"\bmounted\s*:\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{"),
    ]
    for pattern in patterns:
        for m in pattern.finditer(script_text):
            open_brace = script_text.find("{", m.start())
            if open_brace < 0:
                continue
            _, end_idx = _extract_braced_block(script_text, open_brace)
            if end_idx < 0:
                continue
            start_line = _line_number_for_index(script_text, open_brace)
            end_line = _line_number_for_index(script_text, end_idx)
            ranges.append((start_line, end_line))
    return ranges


def _find_promise_callback_ranges(script_text: str) -> List[tuple]:
    ranges: List[tuple] = []
    for m in _PROMISE_HANDLER_RE.finditer(script_text):
        open_paren = script_text.find("(", m.start())
        if open_paren < 0:
            continue
        callback_open = script_text.find("{", open_paren)
        if callback_open < 0:
            continue
        _, end_idx = _extract_braced_block(script_text, callback_open)
        if end_idx < 0:
            continue
        start_line = _line_number_for_index(script_text, callback_open)
        end_line = _line_number_for_index(script_text, end_idx)
        ranges.append((start_line, end_line))
    return ranges


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
