"""
extractors/path_utils.py
========================
Shared path normalization utility used by all tasks.

Converts raw file paths (absolute Windows or relative) into clean,
consistent relative paths suitable for JSON reports and database storage.
"""

import os
from pathlib import PurePosixPath


def normalize_path(raw_path: str, base_path: str) -> str:
    """
    Convert any file path into a clean, consistent relative path.

    Strategy:
        1. Normalize separators to forward-slash on all platforms.
        2. Resolve the absolute path and the base_path to compare them.
        3. If raw_path starts with base_path, strip it to get the relative portion.
        4. If a 'src/' segment exists, keep everything from 'src/' onward.
        5. Otherwise return the path relative to base_path.

    Args:
        raw_path  (str): The file path to normalize (absolute or relative).
        base_path (str): The project's base directory from config (e.g.
                         'C:/Users/.../client/app/src').

    Returns:
        str: A clean relative path like 'src/views/Login.vue' or
             'views/Login.vue'. Never contains backslashes.

    Examples:
        >>> normalize_path('C:\\\\Users\\\\X\\\\src\\\\views\\\\Login.vue',
        ...                'C:/Users/X/src')
        'src/views/Login.vue'

        >>> normalize_path('src/views/Login.vue', 'C:/Users/X/src')
        'src/views/Login.vue'
    """
    if not raw_path:
        return raw_path or ""

    # If base_path is empty/None, we can't strip anything —
    # still normalize separators and return.
    if not base_path:
        return raw_path.replace("\\", "/")

    # Step 1: Normalize separators
    norm = raw_path.replace("\\", "/")
    base = base_path.replace("\\", "/").rstrip("/")

    # Step 2: Try to strip base_path prefix (case-insensitive for Windows)
    norm_lower = norm.lower()
    base_lower = base.lower()

    if norm_lower.startswith(base_lower):
        # Strip base and leading slash
        relative = norm[len(base):].lstrip("/")
        if relative:
            return relative

    # Step 3: If base_path has a trailing directory name, check if it appears in the path
    # e.g. base_path ends with '/src' and path contains '/src/'
    base_tail = base.rsplit("/", 1)[-1].lower()  # e.g. 'src'
    marker = f"/{base_tail}/"
    idx = norm_lower.find(marker)
    if idx >= 0:
        # Return from the marker directory onward: 'src/views/Login.vue'
        return norm[idx + 1:]

    # Step 4: If 'src/' exists anywhere in the path, use it as anchor
    src_idx = norm_lower.find("/src/")
    if src_idx >= 0:
        return norm[src_idx + 1:]

    # Step 5: Fallback — return the path as-is (already relative or unresolvable)
    return norm


def get_all_vue_files(base_path: str) -> list:
    """
    Recursively find ALL .vue files under the given directory,
    excluding node_modules, dist, build artifacts, and other noise.

    Args:
        base_path (str): Root directory to search recursively.

    Returns:
        list[str]: Sorted list of absolute paths to all .vue files found.
    """
    from pathlib import Path

    # Directories that should NEVER be scanned — these contain third-party
    # or generated code that would pollute audit results.
    EXCLUDED_DIRS = {
        "node_modules", "dist", "build", ".nuxt", ".output",
        "coverage", ".git", "__pycache__", ".vscode", ".idea",
    }

    base = Path(base_path).resolve()
    if not base.exists() or not base.is_dir():
        return []

    results = []
    for p in base.rglob("*.vue"):
        # Check if any parent directory is in the exclusion set
        if not any(part in EXCLUDED_DIRS for part in p.parts):
            results.append(str(p))

    return sorted(results)
