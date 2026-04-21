"""
extractors/vue_parser.py
========================
Role in pipeline (Step 1 of 4):
    This module is the ENTRY POINT for every .vue file processed by the
    Code Audit Librarian. It is responsible only for SPLITTING the file
    into its three structural blocks — <template>, <script>, and <style>.

    It uses tree-sitter-vue so that the split is grammar-aware rather than
    a naive string search. After the split, downstream modules receive:
        - template_node : the raw tree-sitter AST node (for template analysis)
        - script_text   : the raw script source text (for cleaning + MQL scan)
        - style_text    : the raw style source text (informational only)

    IMPORTANT — MQL ERROR nodes:
        The Digital University codebase contains proprietary MQL syntax such as
            o.[LoginCopy]
            r.[GetPortalList]
        This is NOT valid JavaScript. tree-sitter-vue will produce ERROR nodes
        when it encounters these constructs inside the <script> block.
        These ERROR nodes are EXPECTED and NORMAL.  This parser logs a debug
        warning and continues — it never crashes on them.

Dependencies:
    pip install tree-sitter tree-sitter-vue
"""

import os
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# tree-sitter imports — handled with a graceful fallback so the module can be
# imported even if the package is not yet installed (useful during CI checks).
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Language, Parser
    # tree-sitter-vue is not available as a standalone PyPI package.
    # tree-sitter-language-pack bundles Vue (and 100+ other grammars)
    # as pre-compiled wheels.  Install with:
    #     pip install tree-sitter tree-sitter-language-pack
    from tree_sitter_language_pack import get_language as _get_ts_language
    _TS_AVAILABLE = True
except ImportError:                         # pragma: no cover
    _TS_AVAILABLE = False
    logging.warning(
        "[vue_parser] tree-sitter or tree-sitter-language-pack is not installed. "
        "Run: pip install tree-sitter tree-sitter-language-pack"
    )

# ---------------------------------------------------------------------------
# Module-level logger — all warnings use this; callers can configure it.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language object — built once at module load time.
# ---------------------------------------------------------------------------
def _build_language():
    """
    Build and return the tree-sitter Language object for Vue.

    This is called once at module load.  The Language object is cached in the
    module-level variable VUE_LANGUAGE so that repeated calls to parse_vue_file
    do not rebuild it.

    We obtain the Vue grammar from ``tree-sitter-language-pack`` which ships
    pre-compiled wheels for Windows, macOS, and Linux — no build toolchain
    required.  The standalone ``tree-sitter-vue`` package does not exist on
    PyPI as of 2025.

    Returns:
        Language  : a ready-to-use tree-sitter Language, or None if unavailable.
    """
    if not _TS_AVAILABLE:
        return None
    try:
        return _get_ts_language('vue')
    except Exception as exc:               # pragma: no cover
        logger.error("[vue_parser] Failed to build VUE Language: %s", exc)
        return None


VUE_LANGUAGE = _build_language()

def _build_ts_language():
    """Build and return tree-sitter Language object for TypeScript."""
    if not _TS_AVAILABLE:
        return None
    try:
        import tree_sitter_typescript
        from tree_sitter import Language
        return Language(tree_sitter_typescript.language_typescript())
    except Exception as exc:
        logger.warning("[vue_parser] Failed to load TypeScript grammar: %s", exc)
        return None

TYPESCRIPT_LANGUAGE = _build_ts_language()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_vue_file(filepath: str) -> dict:
    """
    Parse a single .vue file and split it into template / script / style blocks.

    This function:
      1. Reads the file in BINARY mode (required by tree-sitter).
      2. Parses the full file using the tree-sitter-vue grammar.
      3. Walks the top-level children of the root node to locate the three
         block types.
      4. Returns a dictionary with the raw template AST node and the raw text
         of the script and style blocks.

    ERROR nodes inside the script (caused by non-standard MQL syntax like
    ``o.[LoginCopy]``) are logged at DEBUG level and do NOT cause a crash.
    The script text is still returned in full — script_cleaner.py will strip
    comments and string literals before the regex MQL extractor runs.

    Args:
        filepath (str): Absolute or relative path to the .vue file.

    Returns:
        dict with keys:
            "file"          (str)       : the filepath as supplied
            "template_node" (Node|None) : tree-sitter AST node for <template>
            "script_text"   (str|None)  : raw text content of <script> block
            "style_text"    (str|None)  : raw text content of <style> block

    Raises:
        Nothing — all errors are logged and None values are returned for
        missing/unparseable blocks.  The pipeline is never interrupted.
    """
    result = {
        "file": filepath,
        "template_node": None,
        "script_text": None,
        "style_text": None,
        "is_script_setup": False,
        "script_lang": None,
        "script_ts_tree": None,
    }

    # --- Guard: tree-sitter must be available ---
    if not _TS_AVAILABLE or VUE_LANGUAGE is None:
        logger.error(
            "[vue_parser] tree-sitter is not available; skipping '%s'.", filepath
        )
        return result

    # --- Read file in binary mode (tree-sitter requirement) ---
    try:
        with open(filepath, "rb") as fh:
            source_bytes = fh.read()
    except OSError as exc:
        logger.error("[vue_parser] Cannot read file '%s': %s", filepath, exc)
        return result

    # --- Parse ---
    try:
        parser = Parser(VUE_LANGUAGE)
        tree = parser.parse(source_bytes)
    except Exception as exc:              # pragma: no cover
        logger.error("[vue_parser] tree-sitter parse failed for '%s': %s", filepath, exc)
        return result

    root = tree.root_node

    if root is None:
        logger.warning("[vue_parser] root_node is None for '%s'. Skipping.", filepath)
        return result

    def count_errors(n) -> int:
        count = 1 if n.type == "ERROR" else 0
        for ch in n.children:
            count += count_errors(ch)
        return count

    total_errors = count_errors(root)
    if total_errors > 0:
        logger.warning("[vue_parser] Found %d ERROR node(s) in '%s'.", total_errors, filepath)

    # --- Walk top-level children to extract blocks ---
    # A .vue SFC has three well-known top-level tag types:
    #   template_element  →  maps to <template>
    #   script_element    →  maps to <script>
    #   style_element     →  maps to <style>
    #
    # Any ERROR node at the top level is also noted but not fatal.

    has_error_nodes = False

    for child in root.children:
        node_type = child.type

        if node_type == "ERROR":
            has_error_nodes = True
            logger.debug(
                "[vue_parser] ERROR node at top level in '%s' "
                "(likely proprietary MQL syntax — expected, continuing).",
                filepath,
            )
            continue

        if node_type == "template_element":
            if result["template_node"] is not None:
                logger.warning(
                    "[vue_parser] Multiple <template> blocks found in '%s'; "
                    "using the first one.", filepath
                )
            else:
                result["template_node"] = child

        elif node_type == "script_element":
            if result["script_text"] is not None:
                logger.warning(
                    "[vue_parser] Multiple <script> blocks found in '%s'; "
                    "using the first one.", filepath
                )
            else:
                script_text = _extract_block_text(child, source_bytes, "script", filepath)
                result["script_text"] = script_text

                # Detect <script setup> and <script lang="ts">
                # The start_tag children contain attribute nodes
                for sub in child.children:
                    if sub.type == "start_tag":
                        tag_text = source_bytes[sub.start_byte:sub.end_byte].decode(
                            "utf-8", errors="replace"
                        ).lower()
                        if "setup" in tag_text:
                            result["is_script_setup"] = True
                        # Detect lang="ts" or lang="typescript"
                        if 'lang="ts"' in tag_text or "lang='ts'" in tag_text or \
                           'lang="typescript"' in tag_text or "lang='typescript'" in tag_text:
                            result["script_lang"] = "ts"
                        break

                # Re-parse script block if it's TypeScript
                if result["script_lang"] == "ts" and result["script_text"] and TYPESCRIPT_LANGUAGE:
                    try:
                        ts_parser = Parser(TYPESCRIPT_LANGUAGE)
                        result["script_ts_tree"] = ts_parser.parse(result["script_text"].encode("utf-8"))
                    except Exception as exc:
                        logger.warning("[vue_parser] Failed to parse TS block for '%s': %s", filepath, exc)

        elif node_type == "style_element":
            if result["style_text"] is not None:
                logger.warning(
                    "[vue_parser] Multiple <style> blocks found in '%s'; "
                    "using the first one.", filepath
                )
            else:
                style_text = _extract_block_text(child, source_bytes, "style", filepath)
                result["style_text"] = style_text

    # --- Post-parse sanity checks ---
    if result["template_node"] is None:
        logger.warning("[vue_parser] No <template> block found in '%s'.", filepath)
    if result["script_text"] is None:
        logger.warning("[vue_parser] No <script> block found in '%s'.", filepath)
    if result["style_text"] is None:
        logger.debug("[vue_parser] No <style> block found in '%s' (may be normal).", filepath)

    if has_error_nodes:
        logger.debug(
            "[vue_parser] '%s' contained ERROR nodes (possibly non-standard syntax). "
            "This is expected for files with proprietary framework syntax.", filepath
        )

    return result


def _extract_block_text(block_node, source_bytes: bytes, block_name: str, filepath: str) -> str | None:
    """
    Extract the raw source text of a <script> or <style> block node.

    tree-sitter represents the content of each SFC block as a child node of
    type ``raw_text`` (or similar).  This helper locates that child and
    decodes the bytes back to a UTF-8 string.

    We walk children of the block_node rather than slicing source_bytes by
    node byte offsets so that we return ONLY the inner content (without the
    surrounding open/close tags).

    Args:
        block_node  : tree-sitter Node for the whole <script> or <style> element.
        source_bytes: the original file bytes (needed to slice text).
        block_name  : "script" or "style" (used only for log messages).
        filepath    : original file path (used only for log messages).

    Returns:
        str  : decoded UTF-8 text of the block content, or None on failure.
    """
    # Strategy 1: look for a child whose type contains "raw_text"
    for child in block_node.children:
        if "raw_text" in child.type:
            try:
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            except Exception as exc:
                logger.warning(
                    "[vue_parser] Failed to decode %s raw_text in '%s': %s",
                    block_name, filepath, exc
                )
                return None

    # Strategy 2: fall back to the entire block text minus the opening/closing tags.
    # Some grammar versions expose content differently; use byte-slice of the whole node
    # and strip the first/last line (which contain the <script> and </script> tags).
    logger.debug(
        "[vue_parser] raw_text child not found for <%s> in '%s'; "
        "falling back to full-node byte slice.", block_name, filepath
    )
    try:
        full_text = source_bytes[block_node.start_byte:block_node.end_byte].decode(
            "utf-8", errors="replace"
        )
        lines = full_text.splitlines(keepends=True)
        # Drop first line (<script ...>) and last line (</script>)
        if len(lines) > 2:
            return "".join(lines[1:-1])
        elif len(lines) == 2:
            return ""           # block is empty
        else:
            return full_text    # something very odd; return as-is
    except Exception as exc:
        logger.warning(
            "[vue_parser] Byte-slice fallback failed for <%s> in '%s': %s",
            block_name, filepath, exc
        )
        return None


def get_all_vue_files(base_path: str) -> list[str]:
    """
    Recursively find all .vue files under the given directory.

    This function walks the entire directory tree rooted at ``base_path`` and
    collects the absolute path of every file whose extension is ``.vue``.

    Why this function exists:
        The tool must be able to run against an entire module folder (e.g.,
        ./client/src) rather than a single file.  main.py calls this to build
        the list of files to process.

    Args:
        base_path (str): Root directory to search.  Can be absolute or relative.

    Returns:
        list[str]: Sorted list of absolute paths to all .vue files found.
                   Returns an empty list if the path does not exist or no
                   .vue files are found — never raises.
    """
    base = Path(base_path).resolve()

    if not base.exists():
        logger.warning(
            "[vue_parser] base_path '%s' does not exist. "
            "No .vue files will be processed.", base_path
        )
        return []

    if not base.is_dir():
        logger.warning(
            "[vue_parser] base_path '%s' is not a directory.", base_path
        )
        return []

    # Directories to exclude — third-party libraries and build artifacts
    # would pollute audit results with irrelevant data.
    EXCLUDED_DIRS = {
        "node_modules", "dist", "build", ".nuxt", ".output",
        "coverage", ".git", "__pycache__", ".vscode", ".idea",
    }

    vue_files = sorted(
        str(p) for p in base.rglob("*.vue")
        if not any(part in EXCLUDED_DIRS for part in p.parts)
    )

    if not vue_files:
        logger.warning(
            "[vue_parser] No .vue files found under '%s'.", base_path
        )
    else:
        logger.info(
            "[vue_parser] Found %d .vue file(s) under '%s'.",
            len(vue_files), base_path
        )

    return vue_files


# ---------------------------------------------------------------------------
# Quick self-test — run this file directly to test against sample.vue
# Usage: python extractors/vue_parser.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s %(name)s — %(message)s",
    )

    # Default: parse sample/sample.vue (relative to this file's parent dir)
    script_dir = Path(__file__).parent.parent          # audit_tool/
    default_sample = script_dir / "sample" / "sample.vue"

    target = sys.argv[1] if len(sys.argv) > 1 else str(default_sample)

    print(f"\n{'='*60}")
    print(f"vue_parser self-test")
    print(f"Target file: {target}")
    print(f"{'='*60}\n")

    parsed = parse_vue_file(target)

    # Report results without printing the full AST (it can be huge)
    print(f"  file          : {parsed['file']}")
    print(f"  template_node : {'[OK] present' if parsed['template_node'] else '[MISS] missing'}")
    print(f"  script_text   : {'[OK] ' + str(len(parsed['script_text'])) + ' chars' if parsed['script_text'] else '[MISS] missing'}")
    print(f"  style_text    : {'[OK] ' + str(len(parsed['style_text'])) + ' chars' if parsed['style_text'] else '[MISS] missing (may be normal)'}")

    if parsed["template_node"]:
        tn = parsed["template_node"]
        print(f"\n  template_node details:")
        print(f"    node type   : {tn.type}")
        print(f"    start line  : {tn.start_point[0] + 1}")
        print(f"    end line    : {tn.end_point[0] + 1}")
        print(f"    child count : {len(tn.children)}")

    if parsed["script_text"]:
        lines = parsed["script_text"].splitlines()
        print(f"\n  script_text preview (first 5 lines):")
        for i, ln in enumerate(lines[:5]):
            print(f"    {i+1:>3}: {ln}")

    print(f"\n{'='*60}")
    print("Self-test complete — no crash means MQL ERROR nodes were handled correctly.")
    print(f"{'='*60}\n")
