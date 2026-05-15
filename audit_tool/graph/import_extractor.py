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

def get_aliases(project_path: str) -> dict:
    aliases = {"@": "src", "~": "src"}
    config_path = os.path.join(project_path, "graph_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "aliases" in data:
                    aliases.update(data["aliases"])
        except Exception as e:
            logger.warning(f"Failed to load aliases from {config_path}: {e}")
    return aliases

def walk_for_imports(node, source_bytes: bytes) -> list:
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
    imports = []
    pattern = re.compile(r'(?:import|export)\s+(?:.*?from\s+)?[\'"]([^\'"]+)[\'"]|import\([\'"]([^\'"]+)[\'"]\)')
    for match in pattern.finditer(script_text):
        m = match.group(1) or match.group(2)
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
        logger.warning(f"Tree-sitter parse failed for imports, falling back to regex: {e}")
        return extract_imports_regex(script_text)

def resolve_import_path(raw_import: str, parent_file_abs: str, project_path: str, aliases: dict) -> str:
    is_local = raw_import.startswith('./') or raw_import.startswith('../') or any(raw_import.startswith(alias) for alias in aliases)
    if not is_local:
        return None
        
    ext = os.path.splitext(raw_import)[1].lower()
    if ext in {'.css', '.scss', '.less', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.woff', '.woff2', '.ttf', '.eot', '.json'}:
        return None
        
    resolved_abs = None
    
    for alias, replacement in aliases.items():
        if raw_import.startswith(alias + '/') or raw_import == alias:
            rel_path = raw_import.replace(alias + '/', replacement + '/', 1) if raw_import.startswith(alias + '/') else replacement
            resolved_abs = os.path.join(project_path, rel_path)
            break
            
    if not resolved_abs:
        parent_dir = os.path.dirname(parent_file_abs)
        resolved_abs = os.path.join(parent_dir, raw_import)
        
    resolved_abs = os.path.normpath(resolved_abs)
    
    def file_exists(path):
        return os.path.exists(path) and os.path.isfile(path)
        
    if file_exists(resolved_abs):
        final_path = resolved_abs
    elif file_exists(resolved_abs + '.js'):
        final_path = resolved_abs + '.js'
    elif file_exists(resolved_abs + '.vue'):
        final_path = resolved_abs + '.vue'
    elif file_exists(resolved_abs + '.ts'):
        final_path = resolved_abs + '.ts'
    elif file_exists(os.path.join(resolved_abs, 'index.js')):
        final_path = os.path.join(resolved_abs, 'index.js')
    elif file_exists(os.path.join(resolved_abs, 'index.vue')):
        final_path = os.path.join(resolved_abs, 'index.vue')
    elif file_exists(os.path.join(resolved_abs, 'index.ts')):
        final_path = os.path.join(resolved_abs, 'index.ts')
    else:
        return "UNRESOLVED:" + resolved_abs
        
    try:
        rel = os.path.relpath(final_path, project_path)
        return rel.replace("\\", "/")
    except ValueError:
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
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")
    
    conn.execute("DELETE FROM component_relationships WHERE project_name = ?", (project_name,))
    conn.execute("DELETE FROM unresolved_imports WHERE project_name = ?", (project_name,))
    
    relationships = []
    unresolved = []
    
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
                
            raw_imports = extract_imports_from_js(script_text)
            
            for raw in set(raw_imports):
                resolved = resolve_import_path(raw, file_abs, project_path, aliases)
                if resolved is None:
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
            relationships
        )
    if unresolved:
        conn.executemany(
            """INSERT INTO unresolved_imports 
               (project_name, parent_file, raw_import, reason) 
               VALUES (?, ?, ?, ?)""", 
            unresolved
        )
        
    conn.commit()
    conn.close()
    
    if len(relationships) == 0:
        logger.error(f"Import extraction found 0 local imports for {project_name}. This indicates a path resolution problem or an empty project.")
    else:
        logger.info(f"Extracted {len(relationships)} relationships and {len(unresolved)} unresolved imports.")
