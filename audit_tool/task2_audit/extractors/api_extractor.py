import re
import logging
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml

try:
    from tree_sitter import Language, Parser
    from tree_sitter_language_pack import get_language
    JS_LANGUAGE = get_language('javascript')
    TS_LANGUAGE = get_language('typescript')
    VUE_LANGUAGE = get_language('vue')
    _TS_AVAILABLE = True
except ImportError:
    _TS_AVAILABLE = False
    JS_LANGUAGE = None
    TS_LANGUAGE = None
    VUE_LANGUAGE = None

try:
    import ast_grep_py
    _AG_AVAILABLE = True
except ImportError:
    _AG_AVAILABLE = False

logger = logging.getLogger(__name__)

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
    """Extract all API calls (MQL and Generic) using ast-grep-py and Tree-Sitter ranges."""
    cfg = _load_config(config_path)
    module = cfg.get("module", "unknown")
    
    mql_config = cfg.get("mql", {})
    mql_pattern_str = mql_config.get("pattern", r'\.setActivity\s*\(\s*["\']([rso]\.\[([^\]]+)\])["\']\s*\)')

    calls: List[Dict[str, Any]] = []
    
    # We still use tree-sitter for precise block detection (mounted/loops)
    mounted_ranges = []
    loop_ranges = []
    
    if _TS_AVAILABLE and JS_LANGUAGE and raw_script_text:
        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(raw_script_text.encode("utf-8"))
        root = tree.root_node
        
        # Walk the tree for blocks
        def _walk_blocks(node):
            prop_name = ""
            if node.type in ["method_definition", "pair", "function_declaration"]:
                key_node = node.child_by_field_name("name") or node.child_by_field_name("key")
                if key_node:
                    prop_name = key_node.text.decode("utf-8")
                
                if prop_name in ["mounted", "created", "onMounted"]:
                    mounted_ranges.append((node.start_point[0], node.end_point[0]))

            if node.type == "call_expression":
                fn = node.child_by_field_name("function")
                if fn and fn.type == "identifier" and fn.text.decode("utf-8") == "onMounted":
                    mounted_ranges.append((node.start_point[0], node.end_point[0]))

            # Check for loops
            if node.type in ["for_statement", "for_in_statement", "for_of_statement", "while_statement"]:
                loop_ranges.append((node.start_point[0], node.end_point[0]))
            
            # Check for array methods (forEach, map, filter)
            if node.type == "call_expression":
                fn = node.child_by_field_name("function")
                if fn and fn.type == "member_expression":
                    prop = fn.child_by_field_name("property")
                    if prop and prop.text.decode("utf-8") in ["forEach", "map", "filter"]:
                        loop_ranges.append((node.start_point[0], node.end_point[0]))

            for child in node.children:
                _walk_blocks(child)

        _walk_blocks(root)

    # --- API EXTRACTION (ast-grep-py) ---
    if _AG_AVAILABLE and cleaned_script_text:
        try:
            sg_root = ast_grep_py.SgRoot(cleaned_script_text, "javascript")
            sg_node = sg_root.root()

            # ast-grep patterns for generic API calls
            ag_patterns = {
                "fetch": "fetch($$$)",
                "axios": "axios($$$)",
                "axios_method": "axios.$M($$$)",
                "http": "this.$http($$$)",
                "http_method": "this.$http.$M($$$)"
            }
            
            for key, pattern in ag_patterns.items():
                for match in sg_node.find_all(pattern=pattern):
                    line_idx = match.range().start.line
                    full_text = match.text()
                    method_name = "fetch" if "fetch" in key else ("axios" if "axios" in key else "$http")
                    
                    calls.append({
                        "type": "GENERIC",
                        "method": method_name,
                        "full_match": full_text.splitlines()[0][:100],
                        "in_mounted": any(s <= line_idx <= e for s, e in mounted_ranges),
                        "in_loop": any(s <= line_idx <= e for s, e in loop_ranges),
                        "line_number": line_idx + 1,
                    })
                    
            # ast-grep pattern for MQL chains: .setActivity("...").fetch()
            # MQL calls look like: new MQL().setActivity("o.[Method]").fetch()
            for match in sg_node.find_all(pattern="$OBJ.setActivity($_)"):
                line_idx = match.range().start.line
                full_text = match.text()
                
                # Use regex strictly for extracting the "o.[Method]" name from the ast-grep matched snippet
                # because MQL object chains can have complex dynamic strings.
                mql_regex = re.compile(mql_pattern_str)
                name_match = mql_regex.search(full_text)
                
                if name_match:
                    method_name = name_match.group(1) if name_match.groups() else name_match.group(0)
                    calls.append({
                        "type": "MQL",
                        "method": method_name,
                        "full_match": full_text.splitlines()[0][:100],
                        "in_mounted": any(s <= line_idx <= e for s, e in mounted_ranges),
                        "in_loop": any(s <= line_idx <= e for s, e in loop_ranges),
                        "line_number": line_idx + 1,
                    })
        except Exception as e:
            logger.warning("[api_extractor] ast-grep-py failed: %s", e)

    # Fallback to pure regex if ast-grep-py missed MQL calls or is unavailable
    if not any(c["type"] == "MQL" for c in calls):
        clean_lines = cleaned_script_text.splitlines()
        mql_regex = re.compile(mql_pattern_str)
        
        for line_idx, line in enumerate(clean_lines):
            for match in mql_regex.finditer(line):
                method_name = match.group(1) if match.groups() else match.group(0)
                calls.append({
                    "type": "MQL",
                    "method": method_name,
                    "full_match": match.group(0),
                    "in_mounted": any(s <= line_idx <= e for s, e in mounted_ranges),
                    "in_loop": any(s <= line_idx <= e for s, e in loop_ranges),
                    "line_number": line_idx + 1,
                })

    # Remove strict duplicates if any overlapping matches happened in generic calls
    unique_calls = []
    seen = set()
    for c in calls:
        sig = (c["method"], c["line_number"], c["type"])
        if sig not in seen:
            seen.add(sig)
            unique_calls.append(c)

    calls = unique_calls

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

if __name__ == "__main__":
    pass
