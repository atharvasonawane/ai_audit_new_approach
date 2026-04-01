import json
import re
import sys
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


# ==========================================
# 1. SECURE CONFIGURATION LOADING
# ==========================================
def load_config():
    """Load database credentials securely from .env and project_config.yaml"""
    # Assuming script is run from audit_tool/ or project_root/
    base_dir = Path(__file__).parent
    config_path = base_dir / "config" / "project_config.yaml"

    if not config_path.exists():
        # Fallback for different run contexts
        config_path = Path("audit_tool/config/project_config.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    load_dotenv()
    if "db" not in cfg:
        cfg["db"] = {}

    cfg["db"]["host"] = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
    cfg["db"]["port"] = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
    cfg["db"]["user"] = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv(
        "MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db")
    )
    return cfg


DB_CFG = load_config()

# ==========================================
# IMPORT — prototype_agent.py is one level ABOVE task7/:
# ==========================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from task7 import db_report_loader

# ==========================================
# 2. SYSTEM PROMPT
# Key changes vs previous version:
#   - Opens with "You CANNOT know anything from memory" to kill
#     the root cause of hallucination before it starts.
#   - "ABSOLUTE RULES" block uses NEVER/ALWAYS language that 3B
#     models respond to better than polite suggestions.
#   - Explicitly bans outputting non-tool-call JSON, closing the
#     loophole where the model printed a fake answer as JSON.
# ==========================================
SYSTEM_INSTRUCTIONS = (
    "You are the Code Audit Librarian, an AI assistant analyzing a legacy Vue.js codebase.\n"
    "You have access to a MySQL database. You CANNOT know anything about this codebase from memory.\n"
    "ALL file data, API calls, defects, and flags MUST come from a tool call. Never invent or guess.\n"
    "\n"
    "TOOLS AVAILABLE:\n"
    '- "get_high_risk_files": Returns a list of risky files. Takes no arguments.\n'
    '- "get_file_database_report": Returns API calls, flags, and defects for a specific file. Requires file_path.\n'
    '- "fetch_vue_block": Fetches raw source code of one block from a Vue file.\n'
    "  Requires: file_path (str) and block_type (one of: script, template, style)\n"
    "  IMPORTANT: Always call get_file_database_report FIRST. Never use this tool first.\n"
    "\n"
    "HOW TO CALL A TOOL - STRICT FORMAT:\n"
    "Output ONLY a single raw JSON object on one line. No extra text. No markdown. No code fences.\n"
    'Example: {"name": "get_file_database_report", "arguments": {"file_path": "RoleMgt.vue"}}\n'
    'Example: {"name": "get_high_risk_files", "arguments": {}}\n'
    "\n"
    "ABSOLUTE RULES - NEVER BREAK THESE:\n"
    "1. NEVER invent, fabricate, or guess file data, API calls, defects, or flags.\n"
    "2. NEVER output a JSON object as your final answer. Final answers must ALWAYS be plain English.\n"
    "3. NEVER answer a question about a file without first calling get_file_database_report.\n"
    "4. NEVER answer a question about risky files without first calling get_high_risk_files.\n"
    "5. NEVER agree with the user if they contradict the database. If the database says 9 API calls, and the user says 8, you MUST politely correct them and stick to the database facts.\n"
    "\n"
    "WORKFLOW:\n"
    "Step 1 - User asks about a file -> output only the JSON tool call, nothing else.\n"
    "Step 2 - You receive a TOOL RESULT -> summarize it clearly in plain English for the user.\n"
    "Step 3 - Greetings or meta questions -> answer in plain English, no tool needed.\n"
)

# Rolling window: keep last 6 turns to stay within the 3B model 8192-token context
MAX_HISTORY_TURNS = 6

# ==========================================
# 4. JSON EXTRACTOR
# Handles all real-world 3B model output patterns:
#   - Compact:   {"name": ...}
#   - Spaced:    { "name": ...}
#   - Fenced:
