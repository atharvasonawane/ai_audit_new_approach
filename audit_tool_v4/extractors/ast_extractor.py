"""
ast_extractor.py
================
Phase 3, Step 6 of MASTER_ARCHITECTURE.md.

Structural API-call detection using ast-grep-py (zero regex for parsing).

Strategy:
  1. Walk all .vue and .js/.ts files under base_path
  2. For .vue files: extract the raw <script> block text before parsing
  3. Feed script text into SgRoot(src, "javascript") — the ast-grep AST engine
  4. Run a set of structural patterns (axios.$METHOD, fetch, $http.$METHOD, etc.)
  5. Emit one SARIFResult per match → Category.ARCHITECTURE

Install:
    pip install ast-grep-py

Usage (standalone):
    python ast_extractor.py --base-path /path/to/vue-project

Usage (from run_audit.py):
    from ast_extractor import extract_api_calls
    results = extract_api_calls(base_path)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterator

from ast_grep_py import SgRoot

from schema_models import Category, SARIFResult, Severity

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Directories that must never be walked
SKIP_DIRS = frozenset({
    "node_modules", "dist", ".nuxt", ".output",
    ".git", "coverage", "__pycache__", ".vite",
})

# File extensions to scan
SCAN_EXTENSIONS = frozenset({".vue", ".js", ".ts", ".jsx", ".tsx"})

# ─────────────────────────────────────────────────────────────────────────────
# Structural search patterns
# Each entry: (rule_id, description, ast-grep pattern)
#
# Pattern syntax:
#   $METHOD   — single-node wildcard (captures one AST node)
#   $$$ARGS   — multi-node wildcard (captures 0 or more nodes)
#
# ast-grep matches call expressions structurally — not by text,
# so `axios.get(url, { headers: {} })` and `axios.get(url)` both match.
# ─────────────────────────────────────────────────────────────────────────────

API_PATTERNS: list[tuple[str, str, str]] = [
    # ── axios ────────────────────────────────────────────────────────────────
    ("api/axios-get",     "axios GET call",               "axios.get($$$)"),
    ("api/axios-post",    "axios POST call",              "axios.post($$$)"),
    ("api/axios-put",     "axios PUT call",               "axios.put($$$)"),
    ("api/axios-patch",   "axios PATCH call",             "axios.patch($$$)"),
    ("api/axios-delete",  "axios DELETE call",            "axios.delete($$$)"),
    ("api/axios-request", "axios generic request call",   "axios.request($$$)"),
    ("api/axios-call",    "axios() direct call",          "axios($$$)"),

    # ── fetch ─────────────────────────────────────────────────────────────────
    ("api/fetch",         "native fetch() call",          "fetch($$$)"),

    # ── Vue $http (vue-resource plugin) ──────────────────────────────────────
    ("api/http-get",      "Vue $http GET",                "this.$http.get($$$)"),
    ("api/http-post",     "Vue $http POST",               "this.$http.post($$$)"),
    ("api/http-put",      "Vue $http PUT",                "this.$http.put($$$)"),
    ("api/http-delete",   "Vue $http DELETE",             "this.$http.delete($$$)"),

    # ── XMLHttpRequest ────────────────────────────────────────────────────────
    ("api/xhr-open",      "XMLHttpRequest.open() call",   "new XMLHttpRequest()"),

    # ── useApi / useFetch composables (Nuxt / common Vue patterns) ───────────
    ("api/useFetch",      "useFetch() composable call",   "useFetch($$$)"),
    ("api/useAsyncData",  "useAsyncData() composable",    "useAsyncData($$$)"),
    ("api/useLazyFetch",  "useLazyFetch() composable",    "useLazyFetch($$$)"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Script block extractor for .vue SFCs
# ─────────────────────────────────────────────────────────────────────────────

_SCRIPT_RE = re.compile(
    r"<script(?:\s[^>]*)?>(.+?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def _extract_script_block(vue_source: str) -> tuple[str, int]:
    """
    Extract the first <script> block content from a Vue SFC.

    Returns (script_text, line_offset) where line_offset is the number of
    lines before the script content starts (used to adjust match line numbers
    so they point to the right place in the original .vue file).

    Falls back to the full file content if no <script> tag is found, so the
    extractor still works on plain .js/.ts files.
    """
    match = _SCRIPT_RE.search(vue_source)
    if match:
        prefix      = vue_source[: match.start(1)]
        line_offset = prefix.count("\n")
        return match.group(1), line_offset
    return vue_source, 0


# ─────────────────────────────────────────────────────────────────────────────
# File walker
# ─────────────────────────────────────────────────────────────────────────────

def _walk_files(base_path: str) -> Iterator[Path]:
    """Yield all scannable source files under base_path, skipping SKIP_DIRS."""
    root = Path(base_path)
    for path in root.rglob("*"):
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if path.suffix.lower() in SCAN_EXTENSIONS and path.is_file():
            yield path


# ─────────────────────────────────────────────────────────────────────────────
# Core extractor
# ─────────────────────────────────────────────────────────────────────────────

def extract_api_calls(base_path: str) -> list[SARIFResult]:
    """
    Walk every .vue/.js/.ts file under base_path and structurally search for
    API call patterns using ast-grep-py.

    Returns a flat list[SARIFResult] — one entry per AST match, deduplicated
    by (file, line, rule_id) to avoid double-counting due to overlapping patterns.

    Args:
        base_path: Absolute path to the root of the Vue project to scan.

    Returns:
        list[SARIFResult] with tool_name="ast-grep", category=ARCHITECTURE.
    """
    results:    list[SARIFResult] = []
    seen:       set[tuple]        = set()    # dedup: (rel_path, line, rule_id)
    files_ok    = 0
    files_err   = 0
    total_match = 0

    base = Path(base_path)

    for file_path in _walk_files(base_path):
        # Relative path — already safe (no absolute prefix)
        try:
            rel_path = str(file_path.relative_to(base)).replace("\\", "/")
        except ValueError:
            rel_path = file_path.name

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("[ast_extractor] Cannot read %s: %s", rel_path, exc)
            files_err += 1
            continue

        # Extract script block (with line offset for .vue files)
        script_src, line_offset = _extract_script_block(source)

        if not script_src.strip():
            continue

        try:
            sg_root = SgRoot(script_src, "javascript")
            root_node = sg_root.root()
        except Exception as exc:
            logger.debug("[ast_extractor] SgRoot failed on %s: %s", rel_path, exc)
            files_err += 1
            continue

        files_ok += 1

        # Run every pattern against this file's AST
        for rule_id, description, pattern in API_PATTERNS:
            try:
                matches = root_node.find_all(pattern=pattern)
            except Exception as exc:
                logger.debug("[ast_extractor] Pattern '%s' failed on %s: %s",
                             pattern, rel_path, exc)
                continue

            for match in matches:
                rng    = match.range()
                # line is 0-indexed in ast-grep → convert to 1-indexed + offset
                line   = rng.start.line + 1 + line_offset
                column = rng.start.column

                dedup_key = (rel_path, line, rule_id)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                # Capture the matched source text as snippet (clamped to 2 lines)
                matched_text = match.text()
                snippet      = matched_text[:120] if matched_text else None

                try:
                    results.append(SARIFResult(
                        tool_name = "ast-grep",
                        rule_id   = rule_id,
                        severity  = Severity.INFO,       # API calls are informational
                        category  = Category.ARCHITECTURE,
                        file_path = rel_path,
                        line      = line,
                        column    = column,
                        message   = f"{description} detected at line {line}",
                        snippet   = snippet,
                    ))
                    total_match += 1
                except Exception as exc:
                    logger.debug("[ast_extractor] SARIFResult failed (%s, L%d): %s",
                                 rel_path, line, exc)

    logger.info(
        "[ast_extractor] Scan complete — %d files parsed, %d errors, %d API matches.",
        files_ok, files_err, total_match,
    )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Standalone CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_results(results: list[SARIFResult]) -> None:
    if not results:
        print("No API calls found.")
        return

    from collections import Counter
    by_rule = Counter(r.rule_id for r in results)

    print(f"\n{'='*65}")
    print(f"  AST API Extraction — {len(results)} matches")
    print(f"{'='*65}")
    print(f"  {'Rule':<30} {'Count':>6}")
    print("  " + "-" * 40)
    for rule, count in by_rule.most_common():
        print(f"  {rule:<30} {count:>6}")
    print(f"{'='*65}")
    print(f"\n  Top 20 findings:\n")
    for r in results[:20]:
        print(f"  [{r.rule_id:<25}] {r.file_path}:{r.line}  {r.snippet or '':.60s}")
    print()


def main() -> None:
    logging.basicConfig(
        level  = logging.INFO,
        format = "%(asctime)s  %(levelname)-8s %(name)s -- %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="ast-grep-py structural API call extractor for Vue/JS projects"
    )
    parser.add_argument(
        "--base-path", required=True,
        help="Absolute path to the root of the Vue.js project to scan",
    )
    args = parser.parse_args()

    results = extract_api_calls(args.base_path)
    _print_results(results)


if __name__ == "__main__":
    main()
