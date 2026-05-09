"""
utils/logger.py
───────────────────────────────────────────────────────────────
Centralised logger for the Code Audit Librarian.

Usage (from any module):
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting scan…")
    logger.error("Something went wrong: %s", err)

Output:
    • Console  — clean, human-readable, coloured when the terminal
                 supports ANSI escape codes.
    • scan.log — all levels written to the audit_tool/ directory
                 (or wherever LOG_FILE points).

Both handlers share the same formatter so the output is
identical whether you read the terminal or the log file.
"""

import logging
import sys
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────
LOG_FILE = Path(__file__).resolve().parent.parent / "scan.log"
LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── ANSI colour helpers ────────────────────────────────────────
_RESET = "\033[0m"
_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}


class _ColouredFormatter(logging.Formatter):
    """Formatter that adds ANSI colour codes to the level name."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, _RESET)
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        return super().format(record)


# ── Internal flag — only set up handlers once ──────────────────
_configured = False


def _configure_root_logger() -> None:
    """Attach console + file handlers to the root logger exactly once."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # ── Console handler ────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Use colour formatter only when stdout supports it
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        console_formatter = _ColouredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    else:
        console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler.setFormatter(console_formatter)
    root.addHandler(console_handler)

    # ── File handler ───────────────────────────────────────────
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)          # capture everything to file
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  Call this at module level:

        logger = get_logger(__name__)

    The first call also bootstraps the root logger's handlers so
    you never need to configure logging anywhere else.
    """
    _configure_root_logger()
    return logging.getLogger(name)
