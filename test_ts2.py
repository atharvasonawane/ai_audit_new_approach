import sys
from tree_sitter import Query, QueryCursor, Language
from tree_sitter_language_pack import get_language
import tree_sitter

TS = get_language('typescript')
JS = get_language('javascript')

p = tree_sitter.Parser(TS)
tree = p.parse(b'defineProps<{ title: string, id: number }>()')

print(tree.root_node.sexp())
print(str(tree.root_node))

