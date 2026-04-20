"""
extractors/complexity_checker.py
=================================
Role in pipeline (feeds into flag_engine.py):
    Counts structural complexity metrics using pure tree-sitter S-expression queries.

    Metrics produced:
        lines    (int) : total non-blank lines in the script block
        methods  (int) : number of method function definitions
        computed (int) : number of computed property definitions
        watchers (int) : number of watcher definitions
        max_loop_depth (int): maximum nesting depth of v-for/v-if directives
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from tree_sitter import Parser, Query, QueryCursor
    from tree_sitter_language_pack import get_language as _get_ts_language
    _TS_AVAILABLE = True
    _JS_LANGUAGE  = _get_ts_language("javascript")
    _TS_LANGUAGE  = _get_ts_language("typescript")
    _VUE_LANGUAGE = _get_ts_language("vue")
    
    _JS_METHODS_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^methods$") value: (object) @obj)
    """
    _JS_COMPUTED_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^computed$") value: (object) @obj)
    """
    _JS_WATCHERS_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^watch$") value: (object) @obj)
    """
    
    # Composition API Queries
    _JS_COMP_METHODS_Q_STR = """
    [
      (function_declaration) @m
      (variable_declarator value: (arrow_function) @m)
      (variable_declarator value: (function_expression) @m)
    ]
    """
    _JS_COMP_COMPUTED_Q_STR = """
    (call_expression function: (identifier) @fn (#match? @fn "^computed$")) @c
    """
    _JS_COMP_WATCHERS_Q_STR = """
    (call_expression function: (identifier) @fn (#match? @fn "^(watch|watchEffect|watchPostEffect|watchSyncEffect)$")) @w
    """
    
    _JS_METHODS_Q = Query(_JS_LANGUAGE, _JS_METHODS_Q_STR)
    _JS_COMPUTED_Q = Query(_JS_LANGUAGE, _JS_COMPUTED_Q_STR)
    _JS_WATCHERS_Q = Query(_JS_LANGUAGE, _JS_WATCHERS_Q_STR)
    _JS_COMP_METHODS_Q = Query(_JS_LANGUAGE, _JS_COMP_METHODS_Q_STR)
    _JS_COMP_COMPUTED_Q = Query(_JS_LANGUAGE, _JS_COMP_COMPUTED_Q_STR)
    _JS_COMP_WATCHERS_Q = Query(_JS_LANGUAGE, _JS_COMP_WATCHERS_Q_STR)
    
    _VUE_LOOPS_Q = Query(_VUE_LANGUAGE, """
    (element (start_tag (directive_attribute (directive_name) @dname (#match? @dname "^v(?:-if|-for|-else-if|-else)$")))) @node
    """)

    # Same queries for TS using the TS parser
    _TS_METHODS_Q = Query(_TS_LANGUAGE, _JS_METHODS_Q_STR)
    _TS_COMPUTED_Q = Query(_TS_LANGUAGE, _JS_COMPUTED_Q_STR)
    _TS_WATCHERS_Q = Query(_TS_LANGUAGE, _JS_WATCHERS_Q_STR)
    _TS_COMP_METHODS_Q = Query(_TS_LANGUAGE, _JS_COMP_METHODS_Q_STR)
    _TS_COMP_COMPUTED_Q = Query(_TS_LANGUAGE, _JS_COMP_COMPUTED_Q_STR)
    _TS_COMP_WATCHERS_Q = Query(_TS_LANGUAGE, _JS_COMP_WATCHERS_Q_STR)

except ImportError:
    _TS_AVAILABLE = False
    _JS_LANGUAGE = None
    _TS_LANGUAGE = None
    _VUE_LANGUAGE = None
    logger.warning("[complexity_checker] tree-sitter not installed.")

def _count_object_keys(obj_node) -> int:
    """Count how many properties/methods are in an object literal."""
    if obj_node is None:
        return 0
    return sum(
        1 for c in obj_node.children
        if c.type in ("pair", "method_definition", "shorthand_property_identifier")
    )


def check_complexity(script_text: str, template_node=None, script_lang="js", script_ts_tree=None) -> dict:
    methods  = 0
    computed = 0
    watchers = 0
    max_loop_depth = 0
    lines = sum(1 for l in script_text.splitlines() if l.strip()) if script_text else 0

    if not _TS_AVAILABLE:
        return {"lines": lines, "methods": methods, "computed": computed, "watchers": watchers, "max_loop_depth": max_loop_depth}

    # ----- 1. Script Node Processing -----
    if script_text:
        tree = script_ts_tree
        if tree is None:
            parser = Parser(_TS_LANGUAGE if script_lang == "ts" else _JS_LANGUAGE)
            tree = parser.parse(script_text.encode("utf-8", errors="replace"))

        root = tree.root_node
        
        # Pick the correct queries based on language
        if script_lang == "ts":
            m_q = _TS_METHODS_Q
            c_q = _TS_COMPUTED_Q
            w_q = _TS_WATCHERS_Q
            cm_q = _TS_COMP_METHODS_Q
            cc_q = _TS_COMP_COMPUTED_Q
            cw_q = _TS_COMP_WATCHERS_Q
        else:
            m_q = _JS_METHODS_Q
            c_q = _JS_COMPUTED_Q
            w_q = _JS_WATCHERS_Q
            cm_q = _JS_COMP_METHODS_Q
            cc_q = _JS_COMP_COMPUTED_Q
            cw_q = _JS_COMP_WATCHERS_Q
            
        cursor = QueryCursor(m_q)
        m_caps = cursor.captures(root)
        
        cursor = QueryCursor(c_q)
        c_caps = cursor.captures(root)
        
        cursor = QueryCursor(w_q)
        w_caps = cursor.captures(root)
        
        # Count keys within the captured "obj" dictionaries for Options API
        if "obj" in m_caps and m_caps["obj"]:
            methods = _count_object_keys(m_caps["obj"][0])
        if "obj" in c_caps and c_caps["obj"]:
            computed = _count_object_keys(c_caps["obj"][0])
        if "obj" in w_caps and w_caps["obj"]:
            watchers = _count_object_keys(w_caps["obj"][0])
            
        # Composition API Form if Options API was empty
        if methods == 0 and computed == 0 and watchers == 0:
            cursor = QueryCursor(cm_q)
            methods = len(cursor.captures(root).get("m", []))
            
            cursor = QueryCursor(cc_q)
            computed = len(cursor.captures(root).get("c", []))
            
            cursor = QueryCursor(cw_q)
            watchers = len(cursor.captures(root).get("w", []))

    # ----- 2. Template Nesting (Loops/Cond) -----
    if template_node is not None and _VUE_LANGUAGE:
        try:
            cursor = QueryCursor(_VUE_LOOPS_Q)
            caps = cursor.captures(template_node)
            nodes = caps.get("node", [])
            # Calculate max depth of overlapping nodes
            # Sort by start_byte, maintain a list of active enclosing nodes
            nodes.sort(key=lambda n: n.start_byte)
            active = []
            for node in nodes:
                # Remove nodes from active list that end before the current node starts
                active = [n for n in active if n.end_byte > node.start_byte]
                active.append(node)
                if len(active) > max_loop_depth:
                    max_loop_depth = len(active)
        except Exception as e:
            logger.warning("[complexity_checker] Failed to query template loops: %s", e)

    return {
        "lines": lines,
        "methods": methods,
        "computed": computed,
        "watchers": watchers,
        "max_loop_depth": max_loop_depth,
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)
    BASE        = Path(__file__).parent.parent
    SAMPLE_PATH = str(BASE / "sample" / "sample.vue")

    sys.path.insert(0, str(BASE))
    from extractors.vue_parser import parse_vue_file

    parsed = parse_vue_file(SAMPLE_PATH)
    raw    = parsed.get("script_text") or ""
    tmpl   = parsed.get("template_node")

    result = check_complexity(raw, template_node=tmpl, script_lang=parsed.get("script_lang", "js"), script_ts_tree=parsed.get("script_ts_tree"))

    print("=== complexity_checker.py self-test ===")
    print(f"File  : {SAMPLE_PATH}")
    for k, v in result.items():
        print(f"{k} : {v}")
