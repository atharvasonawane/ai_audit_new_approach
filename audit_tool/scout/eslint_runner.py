"""
scout/eslint_runner.py
───────────────────────────────────────────────────────────────
Runs ESLint via subprocess and parses the JSON output.
"""

import json
import subprocess
from pathlib import Path

from audit_tool.utils.logger import get_logger

logger = get_logger(__name__)


def run_eslint(file_path: str) -> list[dict]:
    """
    Runs ESLint on a specific file and returns a list of findings.
    Degrades gracefully if ESLint is not installed or fails.
    """
    flags = []
    try:
        # Run ESLint via npx to ensure we use the local project version if available
        # We don't want it to fail the python script if ESLint finds errors (exit code 1)
        result = subprocess.run(
            ["npx", "eslint", "--format", "json", file_path],
            capture_output=True,
            text=True,
            check=False
        )

        if not result.stdout:
            # If stdout is empty but there's stderr, something broke
            if result.stderr:
                logger.warning(f"ESLint failed to run on {file_path}: {result.stderr.strip()}")
            return flags

        try:
            eslint_output = json.loads(result.stdout)
            if not eslint_output:
                return flags

            file_findings = eslint_output[0].get("messages", [])
            for finding in file_findings:
                severity = "error" if finding.get("severity") == 2 else "warn"
                flags.append({
                    "rule": finding.get("ruleId", "unknown"),
                    "message": finding.get("message", ""),
                    "severity": severity,
                    "line_number": finding.get("line", 0),
                    "column_number": finding.get("column", 0)
                })

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse ESLint JSON output for {file_path}")

    except Exception as e:
        logger.warning(f"ESLint execution error for {file_path}: {e}")

    return flags
