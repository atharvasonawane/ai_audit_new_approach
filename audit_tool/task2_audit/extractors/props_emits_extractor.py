"""
extractors/props_emits_extractor.py
====================================
Uses Tree-sitter Queries to extract the props and emits contracts from Vue components.
Supports both Options API (props:{}, emits:[]) and Composition API (defineProps, defineEmits).
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    from tree_sitter import Parser, Query, QueryCursor
    from tree_sitter_language_pack import get_language as _get_ts_language
    _TS_AVAILABLE = True
    _JS_LANGUAGE  = _get_ts_language("javascript")
    _TS_LANGUAGE  = _get_ts_language("typescript")
    
    # Options props: { propA: _, propB: _ }
    _OPTIONS_PROPS_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^props$") value: (object (pair key: (property_identifier) @prop_name)))
    """
    
    # Options props array: ['propA', 'propB']
    _OPTIONS_PROPS_ARR_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^props$") value: (array (string (string_fragment) @prop_name)))
    """

    # Options emits array: emits: ['update', 'close']
    _OPTIONS_EMITS_ARR_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^emits$") value: (array (string (string_fragment) @emit_name)))
    """
    
    # Options emits object: emits: { update: null }
    _OPTIONS_EMITS_OBJ_Q_STR = """
    (pair key: (property_identifier) @k (#match? @k "^emits$") value: (object (pair key: (property_identifier) @emit_name)))
    """
    
    # Composition API defineProps([])
    _COMP_PROPS_ARR_Q_STR = """
    (call_expression 
      function: (identifier) @fn (#match? @fn "^defineProps$")
      arguments: (arguments (array (string (string_fragment) @prop_name)))
    )
    """

    # Composition API defineProps({})
    _COMP_PROPS_OBJ_Q_STR = """
    (call_expression 
      function: (identifier) @fn (#match? @fn "^defineProps$")
      arguments: (arguments (object (pair key: (property_identifier) @prop_name)))
    )
    """

    # Composition API defineEmits([])
    _COMP_EMITS_ARR_Q_STR = """
    (call_expression 
      function: (identifier) @fn (#match? @fn "^defineEmits$")
      arguments: (arguments (array (string (string_fragment) @emit_name)))
    )
    """

    # Composition API defineEmits({})
    _COMP_EMITS_OBJ_Q_STR = """
    (call_expression 
      function: (identifier) @fn (#match? @fn "^defineEmits$")
      arguments: (arguments (object (pair key: (property_identifier) @emit_name)))
    )
    """
    
    # TS type-based composition API defineProps<{a: string}>()
    _TS_COMP_PROPS_TYPE_Q_STR = """
    (call_expression
      function: (identifier) @fn (#match? @fn "^defineProps$")
      type_arguments: (type_arguments (object_type (property_signature name: (property_identifier) @prop_name)))
    )
    """

    _JS_OPTIONS_PROPS_Q = Query(_JS_LANGUAGE, _OPTIONS_PROPS_Q_STR)
    _JS_OPTIONS_PROPS_ARR_Q = Query(_JS_LANGUAGE, _OPTIONS_PROPS_ARR_Q_STR)
    _JS_OPTIONS_EMITS_ARR_Q = Query(_JS_LANGUAGE, _OPTIONS_EMITS_ARR_Q_STR)
    _JS_OPTIONS_EMITS_OBJ_Q = Query(_JS_LANGUAGE, _OPTIONS_EMITS_OBJ_Q_STR)

    _JS_COMP_PROPS_ARR_Q = Query(_JS_LANGUAGE, _COMP_PROPS_ARR_Q_STR)
    _JS_COMP_PROPS_OBJ_Q = Query(_JS_LANGUAGE, _COMP_PROPS_OBJ_Q_STR)
    _JS_COMP_EMITS_ARR_Q = Query(_JS_LANGUAGE, _COMP_EMITS_ARR_Q_STR)
    _JS_COMP_EMITS_OBJ_Q = Query(_JS_LANGUAGE, _COMP_EMITS_OBJ_Q_STR)

    # TS Language
    _TS_OPTIONS_PROPS_Q = Query(_TS_LANGUAGE, _OPTIONS_PROPS_Q_STR)
    _TS_OPTIONS_PROPS_ARR_Q = Query(_TS_LANGUAGE, _OPTIONS_PROPS_ARR_Q_STR)
    _TS_OPTIONS_EMITS_ARR_Q = Query(_TS_LANGUAGE, _OPTIONS_EMITS_ARR_Q_STR)
    _TS_OPTIONS_EMITS_OBJ_Q = Query(_TS_LANGUAGE, _OPTIONS_EMITS_OBJ_Q_STR)

    _TS_COMP_PROPS_ARR_Q = Query(_TS_LANGUAGE, _COMP_PROPS_ARR_Q_STR)
    _TS_COMP_PROPS_OBJ_Q = Query(_TS_LANGUAGE, _COMP_PROPS_OBJ_Q_STR)
    _TS_COMP_EMITS_ARR_Q = Query(_TS_LANGUAGE, _COMP_EMITS_ARR_Q_STR)
    _TS_COMP_EMITS_OBJ_Q = Query(_TS_LANGUAGE, _COMP_EMITS_OBJ_Q_STR)

    # Type based queries
    _TS_TYPE_PROPS_Q = Query(_TS_LANGUAGE, _TS_COMP_PROPS_TYPE_Q_STR)

except ImportError:
    _TS_AVAILABLE = False
    _JS_LANGUAGE = None
    _TS_LANGUAGE = None
    logger.warning("[props_emits_extractor] tree-sitter not installed.")

def extract_props_emits(script_text: str, script_lang="js", script_ts_tree=None) -> dict:
    props = []
    emits = []

    if not _TS_AVAILABLE or not script_text:
        return {"props": props, "emits": emits}

    tree = script_ts_tree
    if tree is None:
        parser = Parser(_TS_LANGUAGE if script_lang == "ts" else _JS_LANGUAGE)
        tree = parser.parse(script_text.encode("utf-8", errors="replace"))

    root = tree.root_node
    source_bytes = script_text.encode("utf-8", errors="replace")

    def _get_matches(q, capture_name):
        cursor = QueryCursor(q)
        caps = cursor.captures(root)
        results = []
        for node in caps.get(capture_name, []):
            try:
                name = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
                results.append(name.strip("'\"`"))
            except Exception:
                pass
        return results

    if script_lang == "ts" and _TS_LANGUAGE:
        ps = _get_matches(_TS_OPTIONS_PROPS_Q, "prop_name") + \
             _get_matches(_TS_OPTIONS_PROPS_ARR_Q, "prop_name") + \
             _get_matches(_TS_COMP_PROPS_ARR_Q, "prop_name") + \
             _get_matches(_TS_COMP_PROPS_OBJ_Q, "prop_name") + \
             _get_matches(_TS_TYPE_PROPS_Q, "prop_name")
             
        es = _get_matches(_TS_OPTIONS_EMITS_OBJ_Q, "emit_name") + \
             _get_matches(_TS_OPTIONS_EMITS_ARR_Q, "emit_name") + \
             _get_matches(_TS_COMP_EMITS_ARR_Q, "emit_name") + \
             _get_matches(_TS_COMP_EMITS_OBJ_Q, "emit_name")
    else:
        ps = _get_matches(_JS_OPTIONS_PROPS_Q, "prop_name") + \
             _get_matches(_JS_OPTIONS_PROPS_ARR_Q, "prop_name") + \
             _get_matches(_JS_COMP_PROPS_ARR_Q, "prop_name") + \
             _get_matches(_JS_COMP_PROPS_OBJ_Q, "prop_name")
             
        es = _get_matches(_JS_OPTIONS_EMITS_OBJ_Q, "emit_name") + \
             _get_matches(_JS_OPTIONS_EMITS_ARR_Q, "emit_name") + \
             _get_matches(_JS_COMP_EMITS_ARR_Q, "emit_name") + \
             _get_matches(_JS_COMP_EMITS_OBJ_Q, "emit_name")

    props = list(dict.fromkeys(ps))
    emits = list(dict.fromkeys(es))
    
    return {
        "props": props,
        "emits": emits
    }

if __name__ == "__main__":
    from extractors.vue_parser import parse_vue_file
    import sys
    test_file = r"C:\Users\Atharvaso\Desktop\final_approach\audit_tool\task2_audit\sample\sample.vue"
    try:
        p = parse_vue_file(test_file)
        res = extract_props_emits(p["script_text"], p.get("script_lang", "js"), p.get("script_ts_tree"))
        print(f"Props: {res['props']}")
        print(f"Emits: {res['emits']}")
    except Exception as e:
        print("Test file not found or failed.")
