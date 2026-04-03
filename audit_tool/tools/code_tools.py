import os
import re
from langchain_core.tools import tool

@tool
def fetch_vue_block(file_path: str, block: str) -> str:
    """
    Reads the actual source code of a Vue file from the local disk.
    Args:
        file_path: The absolute Windows path to the .vue file.
        block: One of 'script', 'template', or 'style'.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        # Regex to find the requested block while ignoring case and capturing everything inside
        pattern = re.compile(rf"<{block}[^>]*>(.*?)</{block}>", re.DOTALL | re.IGNORECASE)
        match = pattern.search(raw_text)
        
        if match:
            return match.group(1).strip()
        else:
            return f"Error: Block '{block}' not found in the source code of this file."
            
    except Exception as e:
        return f"Error reading file: {e}"