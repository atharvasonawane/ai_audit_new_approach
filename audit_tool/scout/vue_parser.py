"""
scout/vue_parser.py
───────────────────────────────────────────────────────────────
Uses Python regular expressions to safely parse a raw .vue file 
and split it into clean structural blocks (template, script, style)
to bypass Windows C++ compilation errors for tree-sitter-vue.
"""

import re
from audit_tool.utils.logger import get_logger

logger = get_logger(__name__)

def split_vue_sfc(source_code: str) -> dict[str, str]:
    """
    Parse a Vue Single File Component string and extract the
    raw text content of its top-level blocks.
    """
    blocks = {"template": "", "script": "", "style": ""}

    for tag in ["template", "script", "style"]:
        match = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", source_code, re.DOTALL | re.IGNORECASE)
        if match:
            blocks[tag] = match.group(1).strip()
            
    return blocks
