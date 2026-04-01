import os
from langchain_core.tools import tool
from task2_audit.extractors.vue_parser import parse_vue_file

@tool
def fetch_vue_block(file_path: str, block: str) -> str:
    """Use this tool to read the actual source code of a Vue file. Only call this tool AFTER get_file_report has already confirmed the file exists in the report. Never call this as the first tool."""
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    try:
        parsed_data = parse_vue_file(file_path)
    except Exception as e:
        return f"Error parsing file: {e}"
        
    content = parsed_data.get(block)
    if not content:
        return f"Error: Block '{block}' not found in file."
        
    return str(content)