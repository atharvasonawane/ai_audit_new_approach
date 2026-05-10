"""
scout/eslint_runner.py
───────────────────────────────────────────────────────────────
Runs ESLint via subprocess and parses the JSON output.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from audit_tool.utils.logger import get_logger

logger = get_logger(__name__)

_ESLINT_CACHE: dict[str, str | None] = {}
_PKG_ROOT_CACHE: dict[str, str | None] = {}


def _find_eslint_executable(start_path: Path) -> str | None:
    """
    Find a project-local ESLint binary (preferred) to avoid npx network installs.
    Caches by discovered project root.
    """
    cur = start_path if start_path.is_dir() else start_path.parent
    for _ in range(20):
        key = str(cur)
        if key in _ESLINT_CACHE:
            return _ESLINT_CACHE[key]

        pkg = cur / "package.json"
        if pkg.exists():
            if os.name == "nt":
                candidates = [
                    cur / "node_modules" / ".bin" / "eslint.cmd",
                    cur / "node_modules" / ".bin" / "eslint.ps1",
                    cur / "node_modules" / ".bin" / "eslint.exe",
                ]
            else:
                candidates = [cur / "node_modules" / ".bin" / "eslint"]

            for c in candidates:
                if c.exists():
                    _ESLINT_CACHE[key] = str(c)
                    return str(c)

            _ESLINT_CACHE[key] = None
            return None

        if cur.parent == cur:
            break
        cur = cur.parent

    return None


def _find_package_root(start_path: Path) -> str | None:
    cur = start_path if start_path.is_dir() else start_path.parent
    for _ in range(20):
        key = str(cur)
        if key in _PKG_ROOT_CACHE:
            return _PKG_ROOT_CACHE[key]

        pkg = cur / "package.json"
        if pkg.exists():
            _PKG_ROOT_CACHE[key] = str(cur)
            return str(cur)

        if cur.parent == cur:
            break
        cur = cur.parent

    return None


def run_eslint(file_path: str) -> list[dict]:
    """
    Runs ESLint on a specific file and returns a list of findings.
    Degrades gracefully if ESLint is not installed or fails.
    """
    flags = []
    try:
        use_npx = os.getenv("AUDIT_USE_NPX_ESLINT", "").strip().lower() in {"1", "true", "yes"}

        # Prefer a local ESLint binary if available (fast, offline, consistent).
        eslint_local = _find_eslint_executable(Path(file_path))
        if eslint_local:
            result = subprocess.run(
                [eslint_local, "--format", "json", file_path],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            # Try a globally available eslint first (fast, no network).
            eslint_global = shutil.which("eslint") or (shutil.which("eslint.cmd") if os.name == "nt" else None)
            if eslint_global:
                result = subprocess.run(
                    [eslint_global, "--format", "json", file_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                if not use_npx:
                    logger.warning("ESLint skipped for %s: no local/global eslint detected", file_path)
                    return flags

                # Optional npx fallback (can be slow; disabled by default).
                pkg_root = _find_package_root(Path(file_path))
                if not pkg_root:
                    logger.warning("ESLint skipped for %s: no Node project (package.json) detected", file_path)
                    return flags

                npx_path = shutil.which("npx")
                if not npx_path and os.name == "nt":
                    npx_path = shutil.which("npx.cmd") or shutil.which("npx.exe")

                if not npx_path:
                    logger.warning("ESLint skipped for %s: npx not found in PATH", file_path)
                    return flags

                if os.name == "nt":
                    cmd = f"\"{npx_path}\" --no-install eslint --format json \"{file_path}\""
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        shell=True,
                        timeout=15,
                        cwd=pkg_root,
                    )
                else:
                    result = subprocess.run(
                        [npx_path, "--no-install", "eslint", "--format", "json", file_path],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=15,
                        cwd=pkg_root,
                    )

        if not result.stdout:
            # If stdout is empty but there's stderr, something broke
            if result.stderr:
                stderr_preview = "\n".join(result.stderr.strip().splitlines()[:4])
                logger.warning("ESLint failed to run on %s: %s", file_path, stderr_preview)
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
            logger.warning("Failed to parse ESLint JSON output for %s", file_path)

    except Exception as e:
        logger.warning("ESLint execution error for %s: %s", file_path, e)

    return flags
