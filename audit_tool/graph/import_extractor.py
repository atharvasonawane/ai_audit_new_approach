import os
import json
import sqlite3
import logging
import re
from pathlib import Path

try:
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language as _get_ts_language
    JS_LANGUAGE = _get_ts_language('javascript')
    TS_AVAILABLE = True
except ImportError:
    JS_LANGUAGE = None
    TS_AVAILABLE = False

try:
    from extractors.vue_parser import parse_vue_file
except ImportError:
    from task2_audit.extractors.vue_parser import parse_vue_file

logger = logging.getLogger("import_extractor")

INCLUDE_EXTENSIONS = {'.vue', '.js', '.ts'}
EXCLUDE_DIRS = {'node_modules', '.git', 'dist', 'build', '.nuxt', '__pycache__'}

# Extensions that are clearly assets — skip without warning
ASSET_EXTENSIONS = {
    '.css', '.scss', '.less', '.sass', '.svg', '.png', '.jpg', '.jpeg',
    '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json',
    '.md', '.txt', '.yaml', '.yml',
}


def _find_src_dir(project_path: str) -> str:
    """
    Find the shallowest 'src' directory inside project_path.
    Prefers the one closest to the root (depth 1) over deeply nested ones.
    Searches up to 5 levels deep. Falls back to project_path if nothing found.

    Using the shallowest match ensures that a standard Vue CLI / Vite project
    with src/ at the root is handled correctly, while still finding deeply
    nested src/ dirs (e.g. monorepos) when needed.
    """
    best = None
    best_depth = 999

    for root, dirs, _ in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        try:
            depth = os.path.relpath(root, project_path).count(os.sep)
        except ValueError:
            continue
        if depth > 5:
            dirs.clear()
            continue
        if 'src' in dirs:
            candidate = os.path.join(root, 'src')
            if depth < best_depth:
                best = candidate
                best_depth = depth
            # Once we have a depth-0 or depth-1 hit, stop immediately
            if depth <= 1:
                break

    if best:
        logger.info(f"[alias resolver] Auto-detected src/ at: {best} (depth {best_depth})")
        return best

    logger.warning(
        f"[alias resolver] No 'src' directory found under {project_path} "
        f"(searched 5 levels). @ and ~ will resolve to project root."
    )
    return project_path


def _read_aliases_from_tsconfig(project_path: str) -> dict:
    """
    Read compilerOptions.paths from tsconfig.json or jsconfig.json.
    These are the canonical alias sources for TypeScript and modern Vite projects.

    Example tsconfig.json entry:
        "paths": { "@/*": ["src/*"] }
    → We strip the trailing /* to get the directory mapping.
    """
    aliases = {}
    for config_name in ('tsconfig.json', 'jsconfig.json'):
        config_file = os.path.join(project_path, config_name)
        if not os.path.exists(config_file):
            continue
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                # Strip JS-style comments before parsing (tsconfig allows them)
                text = re.sub(r'/\*.*?\*/', '', f.read(), flags=re.DOTALL)
                text = re.sub(r'//[^\n]*', '', text)
                data = json.loads(text)
            paths = data.get('compilerOptions', {}).get('paths', {})
            base_url = data.get('compilerOptions', {}).get('baseUrl', '.')
            base_abs = os.path.normpath(os.path.join(project_path, base_url))
            for alias_key, targets in paths.items():
                # Normalise "@/*" → "@", "@" → "@"
                clean_key = alias_key.rstrip('/*').rstrip('/')
                if not clean_key:
                    continue
                if isinstance(targets, list) and targets:
                    raw_target = targets[0].rstrip('/*').rstrip('/')
                    abs_target = os.path.normpath(os.path.join(base_abs, raw_target))
                    aliases[clean_key] = abs_target
                    logger.info(
                        f"[alias resolver] {config_name}: '{clean_key}' → {abs_target}"
                    )
        except Exception as exc:
            logger.warning(f"[alias resolver] Could not parse {config_file}: {exc}")
    return aliases


def _read_aliases_from_vite_config(project_path: str) -> dict:
    """
    Extract alias definitions from vite.config.js/ts or vue.config.js via regex.
    This is a best-effort extraction — it handles the common pattern:
        alias: { '@': path.resolve(__dirname, 'src') }
    but cannot execute arbitrary JS.
    """
    aliases = {}
    config_files = (
        'vite.config.js', 'vite.config.ts',
        'vue.config.js', 'vue.config.ts',
        'webpack.config.js',
    )
    # Matches: '@': ...'src'  OR  '@': path.resolve(..., 'src')
    # Group 1 = alias key, Group 2 = last string argument (the dir name)
    pattern = re.compile(
        r"""['"]([@~][^'"]*)['"] *: *(?:path\.resolve\([^)]+, *)?[\'\"]([^\'\"]+)[\'\"]"""
    )
    for cfg in config_files:
        cfg_path = os.path.join(project_path, cfg)
        if not os.path.exists(cfg_path):
            continue
        try:
            text = Path(cfg_path).read_text(encoding='utf-8')
            for m in pattern.finditer(text):
                key = m.group(1).rstrip('/')
                raw_dir = m.group(2).strip('/')
                abs_dir = os.path.normpath(os.path.join(project_path, raw_dir))
                if os.path.isdir(abs_dir):
                    aliases[key] = abs_dir
                    logger.info(
                        f"[alias resolver] {cfg}: '{key}' → {abs_dir}"
                    )
        except Exception as exc:
            logger.warning(f"[alias resolver] Could not read {cfg_path}: {exc}")
    return aliases


def get_aliases(project_path: str) -> dict:
    """
    Build the alias map for a project using a priority chain:

    1. tsconfig.json / jsconfig.json  compilerOptions.paths  (most authoritative)
    2. vite.config.js / vue.config.js  resolve.alias  (regex extraction)
    3. Auto-detected shallowest src/ directory
    4. Falls back to project root

    The result always uses absolute paths so os.path.join downstream works
    regardless of the working directory. Supports any Vue/JS project structure.

    Custom overrides: place a graph_config.json at the project root with:
        { "aliases": { "@": "path/relative/to/project" } }
    """
    # Priority 1 & 2 — read from the project's own config files
    aliases = {}
    tsconfig_aliases = _read_aliases_from_tsconfig(project_path)
    aliases.update(tsconfig_aliases)

    vite_aliases = _read_aliases_from_vite_config(project_path)
    for k, v in vite_aliases.items():
        if k not in aliases:  # tsconfig takes priority
            aliases[k] = v

    # Priority 3 — fill in @ and ~ if they weren't declared in any config file
    if '@' not in aliases or '~' not in aliases:
        real_src = _find_src_dir(project_path)
        if '@' not in aliases:
            aliases['@'] = real_src
        if '~' not in aliases:
            aliases['~'] = real_src

    # Priority 4 — manual override via graph_config.json
    config_path = os.path.join(project_path, 'graph_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'aliases' in data:
                for k, v in data['aliases'].items():
                    abs_v = os.path.normpath(
                        v if os.path.isabs(v) else os.path.join(project_path, v)
                    )
                    aliases[k] = abs_v
                logger.info(
                    f"[alias resolver] graph_config.json overrides applied: {data['aliases']}"
                )
        except Exception as e:
            logger.warning(f"[alias resolver] Failed to load graph_config.json: {e}")

    logger.info(f"[alias resolver] Final alias map: { {k: v for k, v in aliases.items()} }")
    return aliases


def walk_for_imports(node, source_bytes: bytes) -> list:
    """Tree-sitter AST walk — catches static imports, re-exports, and dynamic import() calls."""
    imports = []
    if node.type in ('import_statement', 'export_statement'):
        source_node = node.child_by_field_name('source')
        if source_node and source_node.type == 'string':
            text = source_bytes[source_node.start_byte:source_node.end_byte].decode("utf8", errors="replace")
            imports.append(text.strip("\"'`"))
    elif node.type == 'call_expression':
        func_node = node.child_by_field_name('function')
        if func_node and func_node.type == 'import':
            args_node = node.child_by_field_name('arguments')
            if args_node:
                for arg in args_node.children:
                    if arg.type == 'string':
                        text = source_bytes[arg.start_byte:arg.end_byte].decode("utf8", errors="replace")
                        imports.append(text.strip("\"'`"))
    for child in node.children:
        imports.extend(walk_for_imports(child, source_bytes))
    return imports


def extract_imports_regex(script_text: str) -> list:
    """
    Regex fallback import extractor.
    Catches:
      - import X from '...'
      - import('...')           (dynamic/lazy-loaded)
      - export ... from '...'
      - require('...')
    """
    imports = []
    # Static/dynamic import and export ... from
    pattern = re.compile(
        r'(?:import|export)\s+(?:.*?from\s+)?[\'"]([^\'"]+)[\'"]'
        r'|import\([\'"]([^\'"]+)[\'"]\)'
        r'|require\([\'"]([^\'"]+)[\'"]\)'
    )
    for match in pattern.finditer(script_text):
        m = match.group(1) or match.group(2) or match.group(3)
        if m:
            imports.append(m)
    return imports


def extract_imports_from_js(script_text: str) -> list:
    if not TS_AVAILABLE or not JS_LANGUAGE:
        return extract_imports_regex(script_text)

    try:
        parser = Parser(JS_LANGUAGE)
        source_bytes = script_text.encode("utf8")
        tree = parser.parse(source_bytes)
        return walk_for_imports(tree.root_node, source_bytes)
    except Exception as e:
        logger.warning(f"Tree-sitter parse failed, falling back to regex: {e}")
        return extract_imports_regex(script_text)


def resolve_import_path(
    raw_import: str,
    parent_file_abs: str,
    project_path: str,
    aliases: dict,
    parent_rel: str = "",  # for warning messages
) -> str:
    """
    Resolve a raw import string to a project-relative path.

    Returns:
      - A relative path string (e.g. "src/components/Header.vue")  on success
      - None  if the import is a package, asset, or intentionally skipped
      - "UNRESOLVED:<abs_path>" if it looks local but the file can't be found on disk

    WARNING logs are emitted for every UNRESOLVED local import so nothing is silently dropped.
    """
    # --- Determine if this is a local import ---
    is_aliased = any(
        raw_import == alias or raw_import.startswith(alias + '/')
        for alias in aliases
    )
    is_relative = raw_import.startswith('./') or raw_import.startswith('../')
    is_local = is_relative or is_aliased

    if not is_local:
        # Pure npm package — not a warning, just skip
        return None

    # --- Skip asset-only imports ---
    ext = os.path.splitext(raw_import)[1].lower()
    if ext in ASSET_EXTENSIONS:
        return None

    # --- Resolve alias → absolute path ---
    resolved_abs = None

    for alias, replacement in aliases.items():
        if raw_import == alias:
            resolved_abs = replacement
            break
        if raw_import.startswith(alias + '/'):
            tail = raw_import[len(alias) + 1:]
            resolved_abs = os.path.join(replacement, tail)
            break

    if not resolved_abs:
        parent_dir = os.path.dirname(parent_file_abs)
        resolved_abs = os.path.join(parent_dir, raw_import)

    resolved_abs = os.path.normpath(resolved_abs)

    # --- Try extensions in priority order ---
    def file_exists(path):
        return os.path.exists(path) and os.path.isfile(path)

    candidates = [
        resolved_abs,
        resolved_abs + '.vue',
        resolved_abs + '.js',
        resolved_abs + '.ts',
        os.path.join(resolved_abs, 'index.vue'),
        os.path.join(resolved_abs, 'index.js'),
        os.path.join(resolved_abs, 'index.ts'),
    ]

    final_path = None
    for candidate in candidates:
        if file_exists(candidate):
            final_path = candidate
            break

    if final_path is None:
        label = parent_rel or parent_file_abs
        logger.warning(
            f"[unresolved import] '{raw_import}' in '{label}' "
            f"→ tried {len(candidates)} candidates, none found on disk. "
            f"First candidate: {candidates[0]}"
        )
        return "UNRESOLVED:" + resolved_abs

    try:
        rel = os.path.relpath(final_path, project_path)
        return rel.replace("\\", "/")
    except ValueError:
        logger.warning(
            f"[unresolved import] '{raw_import}' in '{parent_rel or parent_file_abs}' "
            f"→ resolved outside project root: {final_path}"
        )
        return "UNRESOLVED:" + final_path


def classify_relationship(child_file_rel: str) -> str:
    path = child_file_rel.lower()
    if '/composables/' in path or '/composable/' in path:
        return 'composable'
    elif '/store/' in path or '/stores/' in path:
        return 'store'
    elif '/services/' in path or '/service/' in path or '/api/' in path:
        return 'service'
    elif '/router/' in path or '/routes/' in path:
        return 'router'
    elif path.endswith('.vue'):
        return 'component'
    else:
        return 'utility'


def run_import_extraction(project_path: str, project_name: str, db_path: str):
    logger.info(f"Starting import extraction for '{project_name}' at '{project_path}'")
    aliases = get_aliases(project_path)
    logger.info(f"[alias resolver] Active aliases: { {k: v for k, v in aliases.items()} }")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute("DELETE FROM component_relationships WHERE project_name = ?", (project_name,))
    conn.execute("DELETE FROM unresolved_imports WHERE project_name = ?", (project_name,))

    relationships = []
    unresolved = []

    total_files_scanned = 0
    total_imports_found = 0
    total_skipped_packages = 0
    total_skipped_assets = 0

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in INCLUDE_EXTENSIONS:
                continue

            file_abs = os.path.join(root, file)
            try:
                parent_rel = os.path.relpath(file_abs, project_path).replace("\\", "/")
            except ValueError:
                continue

            script_text = ""
            if ext == '.vue':
                try:
                    parsed = parse_vue_file(file_abs)
                    if parsed.get("script_text"):
                        script_text = parsed["script_text"]
                except Exception as e:
                    logger.warning(f"Failed to parse vue file {file_abs}: {e}")
            elif ext in ('.js', '.ts'):
                try:
                    with open(file_abs, "r", encoding="utf-8") as f:
                        script_text = f.read()
                except Exception as e:
                    logger.warning(f"Failed to read file {file_abs}: {e}")

            if not script_text:
                continue

            total_files_scanned += 1
            raw_imports = extract_imports_from_js(script_text)
            unique_imports = set(raw_imports)
            total_imports_found += len(unique_imports)

            for raw in unique_imports:
                # Pre-classify before calling resolve so we can count skips accurately
                is_aliased = any(
                    raw == alias or raw.startswith(alias + '/')
                    for alias in aliases
                )
                is_relative = raw.startswith('./') or raw.startswith('../')
                is_local = is_relative or is_aliased
                raw_ext = os.path.splitext(raw)[1].lower()

                if not is_local:
                    total_skipped_packages += 1
                    continue
                if raw_ext in ASSET_EXTENSIONS:
                    total_skipped_assets += 1
                    continue

                resolved = resolve_import_path(raw, file_abs, project_path, aliases, parent_rel)

                if resolved is None:
                    # Should not happen after pre-classification, but guard anyway
                    continue
                elif resolved.startswith("UNRESOLVED:"):
                    unresolved.append((project_name, parent_rel, raw, "file_not_found"))
                else:
                    if parent_rel != resolved:
                        rel_type = classify_relationship(resolved)
                        relationships.append((project_name, parent_rel, resolved, rel_type))

    if relationships:
        conn.executemany(
            """INSERT OR IGNORE INTO component_relationships
               (project_name, parent_file, child_file, relationship_type)
               VALUES (?, ?, ?, ?)""",
            relationships,
        )
    if unresolved:
        conn.executemany(
            """INSERT INTO unresolved_imports
               (project_name, parent_file, raw_import, reason)
               VALUES (?, ?, ?, ?)""",
            unresolved,
        )

    conn.commit()
    conn.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("[import_extractor] Extraction Summary")
    logger.info(f"  Files scanned       : {total_files_scanned}")
    logger.info(f"  Import strings found: {total_imports_found}")
    logger.info(f"  Skipped (packages)  : {total_skipped_packages}")
    logger.info(f"  Skipped (assets)    : {total_skipped_assets}")
    logger.info(f"  Resolved edges      : {len(relationships)}")
    logger.info(f"  Unresolved imports  : {len(unresolved)}")
    logger.info("=" * 60)

    if len(relationships) == 0:
        logger.error(
            f"Import extraction found 0 local imports for {project_name}. "
            f"This indicates a path resolution problem or an empty project. "
            f"Check the alias resolver warnings above."
        )
    else:
        logger.info(
            f"Extracted {len(relationships)} relationships and {len(unresolved)} unresolved imports."
        )
