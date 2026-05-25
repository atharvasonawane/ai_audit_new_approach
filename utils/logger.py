import logging
import sys

# Standardized unified logger for the Code Audit Librarian codebase
logger = logging.getLogger("code_audit")

# Avoid adding duplicate handlers if they are already configured in the parent / root logger
if not logger.handlers:
    logger.setLevel(logging.INFO)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Match standard logging format: HH:MM:SS LEVEL Name -- Message
    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s %(name)s -- %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Also add standard scan.log file handler if possible
    try:
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        file_handler = logging.FileHandler(str(project_root / "scan.log"), encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
    except Exception:
        pass
