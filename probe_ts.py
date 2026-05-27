"""Full verification of the tree-sitter AST import extractor — 10 patterns."""
import sys, logging
logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, 'audit_tool')
from graph.import_extractor import extract_imports_from_js

TESTS = [
    ("Static import (single quotes)",            "import Header from './Header'",                                    ["./Header"]),
    ("Static import with @/ alias",              "import { foo } from '@/utils/foo'",                               ["@/utils/foo"]),
    ("Re-export statement",                      "export { bar } from '../bar'",                                    ["../bar"]),
    ("Dynamic import + webpack magic comment",   "const A = () => import(/* webpackChunkName: 'c' */ './A.vue')",   ["./A.vue"]),
    ("Dynamic import + backtick template",       "const B = () => import(`./B.vue`)",                               ["./B.vue"]),
    ("CommonJS require()",                       "const C = require('./C.js')",                                     ["./C.js"]),
    ("Dynamic import + trailing comment",        "const D = () => import('./D' /* trailing */)",                    ["./D"]),
    ("Dynamic import + multiple webpack comments","const E = () => import(\n    /* webpackChunkName: 'x' */\n    /* webpackPrefetch: true */\n    './E.vue'\n)", ["./E.vue"]),
    ("Dynamic template with variable — flagged", "const X = () => import(`./views/${name}.vue`)",                  ["./views/${name}.vue"]),
    ("npm package — extracted, filtered later",  "import Vue from 'vue'",                                           ["vue"]),
]

print("=" * 60)
print("Verification Suite — tree-sitter AST import extractor")
print("=" * 60)
passed = failed = 0
for label, code, expected in TESTS:
    result = extract_imports_from_js(code)
    ok = sorted(result) == sorted(expected)
    status = "PASS" if ok else "FAIL"
    passed += ok; failed += (not ok)
    print(f"\n[{status}] {label}")
    if not ok:
        print(f"  Expected : {expected}")
        print(f"  Got      : {result}")

print(f"\n{'='*60}")
print(f"Results: {passed}/{len(TESTS)} passed  |  {failed} failed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
