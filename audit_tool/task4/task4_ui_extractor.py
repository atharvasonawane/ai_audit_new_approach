"""
task4/task4_ui_extractor.py
===========================
Role in pipeline:
    Standalone script that extracts UI elements (buttons, headers, visible text)
    from all .vue files in src/components and src/views.
    Uses tree-sitter `<template>` AST nodes from task2_audit.extractors.vue_parser.
    Outputs a structured JSON `ui_extraction.json` preserving static and i18n texts.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup paths
BASE = Path(__file__).parent.parent
TASK2_BASE = BASE / "task2_audit"
CONFIG_PATH = str(TASK2_BASE / "config" / "project_config.yaml")

sys.path.insert(0, str(TASK2_BASE))
import yaml
from extractors.vue_parser import parse_vue_file
from db.db_writer import _get_connection, _get_file_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s")
logger = logging.getLogger("task4_ui_extractor")

HEADER_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "pageheader", "baseheader"}

def get_node_tag_name(node, source_bytes):
    for child in node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for sub in child.children:
                if sub.type == "tag_name":
                    return source_bytes[sub.start_byte:sub.end_byte].decode("utf-8").strip().lower()
    return ""

def get_node_attribute(node, source_bytes, attr_name):
    for child in node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for attr in child.children:
                if attr.type == "attribute":
                    n = v = ""
                    for sub in attr.children:
                        if sub.type == "attribute_name":
                            n = source_bytes[sub.start_byte:sub.end_byte].decode("utf-8").strip()
                        elif sub.type == "quoted_attribute_value":
                            for subval in sub.children:
                                if subval.type == "attribute_value":
                                    v = source_bytes[subval.start_byte:subval.end_byte].decode("utf-8")
                    if n == attr_name:
                        return v
    return ""

def extract_text_and_type(root_node, source_bytes):
    texts = []
    is_static = False
    is_i18n = False

    def walk(node):
        nonlocal is_static, is_i18n
        if node.type == "text":
            val = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
            if val.strip():
                is_static = True
            texts.append(val)
        elif node.type == "interpolation":
            val = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
            is_i18n = True
            texts.append(val)
        else:
            for child in node.children:
                walk(child)
                
    walk(root_node)
    return ("".join(texts).strip(), is_static, is_i18n)

def get_text_type(is_static, is_i18n):
    if is_static and is_i18n:
        return "mixed"
    elif is_i18n:
        return "i18n"
    elif is_static:
        return "static"
    return "static"

def is_valid_visible_text(text_str):
    if not text_str:
        return False
    if len(text_str) < 2:
        return False
    if text_str.isnumeric():
        return False
    return True

def process_vue_file(file_path):
    with open(file_path, "rb") as f:
        source_bytes = f.read()
    
    parsed = parse_vue_file(str(file_path))
    template_node = parsed.get("template_node")
    
    norm_path = str(file_path).replace("\\", "/")
    if "src/" in norm_path:
        clean_file_path = "src/" + norm_path.split("src/")[-1]
    else:
        clean_file_path = norm_path
        
    result = {
        "file": clean_file_path,
        "raw_file_path": str(Path(file_path).resolve()),
        "uses_i18n": False,
        "buttons": [],
        "headers": [],
        "visibleTexts": []
    }
    
    if not template_node:
        return result
        
    seen_buttons = set()
    seen_headers = set()
    seen_visible = set()

    def walk_template(node):
        if node.type in ("element", "self_closing_element"):
            tag = get_node_tag_name(node, source_bytes)
            
            # --- 1. Button ---
            if tag == "button":
                cls = get_node_attribute(node, source_bytes, "class")
                text_val, is_static, is_i18n = extract_text_and_type(node, source_bytes)
                
                if is_i18n:
                    result["uses_i18n"] = True
                    
                is_icon_only = True
                for child in node.children:
                    if child.type == "interpolation":
                        is_icon_only = False
                    elif child.type == "text":
                        val = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                        if val.strip():
                            is_icon_only = False
                
                if not is_icon_only and text_val:
                    dedup_key = f"{text_val}|{cls}"
                    if dedup_key not in seen_buttons:
                        seen_buttons.add(dedup_key)
                        result["buttons"].append({
                            "text": text_val,
                            "type": get_text_type(is_static, is_i18n),
                            "class": cls
                        })
                return # Skip subtree

            # --- 2. Header ---
            if tag in HEADER_TAGS:
                text_val, is_static, is_i18n = extract_text_and_type(node, source_bytes)
                
                title_attr = ""
                if tag in ("pageheader", "baseheader"):
                    title_attr = get_node_attribute(node, source_bytes, "title").strip()
                    
                final_text = title_attr if title_attr else text_val
                final_type = get_text_type(is_static, is_i18n)
                
                if title_attr:
                    final_type = "static"
                    
                if is_i18n or "{{" in final_text:
                    result["uses_i18n"] = True
                    if "{{" in final_text and title_attr:
                        final_type = "i18n"
                
                if final_text and final_text not in seen_headers:
                    seen_headers.add(final_text)
                    result["headers"].append({
                        "text": final_text,
                        "type": final_type
                    })
                return # Skip subtree

        # --- 3. Visible Text ---
        if node.type in ("element", "self_closing_element"):
            direct_texts = []
            d_static = False
            d_i18n = False
            
            for child in node.children:
                if child.type == "text":
                    val = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                    if val.strip(): d_static = True
                    direct_texts.append(val)
                elif child.type == "interpolation":
                    val = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                    d_i18n = True
                    direct_texts.append(val)
            
            combined = "".join(direct_texts).strip()
            if is_valid_visible_text(combined):
                if d_i18n or "{{" in combined:
                    result["uses_i18n"] = True
                if combined not in seen_visible:
                    seen_visible.add(combined)
                    result["visibleTexts"].append({
                        "text": combined,
                        "type": get_text_type(d_static, d_i18n)
                    })

        for child in node.children:
            walk_template(child)

    walk_template(template_node)
    
    # Check if there are interpolations in buttons or headers to set uses_i18n
    if not result["uses_i18n"]:
        for el in result["buttons"] + result["headers"]:
            if el["type"] in ("i18n", "mixed") or "{{" in el["text"]:
                result["uses_i18n"] = True
                break

    return result

def main():
    if not Path(CONFIG_PATH).exists():
        logger.error(f"Config not found at {CONFIG_PATH}")
        sys.exit(1)
        
    cfg = yaml.safe_load(open(CONFIG_PATH, encoding="utf-8"))
    
    from dotenv import load_dotenv
    load_dotenv()
    if "db" not in cfg:
        cfg["db"] = {}
    cfg["db"]["host"]     = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
    cfg["db"]["port"]     = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
    cfg["db"]["user"]     = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv("MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db"))

    base_path = cfg.get("base_path", "")
    
    if not base_path:
        logger.error("base_path not defined in config")
        sys.exit(1)
        
    base_dir = BASE / Path(base_path)
    components_dir = base_dir / "components"
    views_dir = base_dir / "views"
    
    # Note: Using absolute path resolution considering run_audit location.
    # The config base_path is "./client/src", so BASE / "./client/src/components"
    
    vue_files = []
    if components_dir.exists():
        vue_files.extend(list(components_dir.rglob("*.vue")))
    if views_dir.exists():
        vue_files.extend(list(views_dir.rglob("*.vue")))
        
    # Also include the sample adminLogin.vue for testing if it's at project root
    sample_admin = BASE.parent / "adminLogin.vue"
    if sample_admin.exists() and sample_admin not in vue_files:
        vue_files.append(sample_admin)
        
    logger.info(f"Found {len(vue_files)} .vue files in components/ and views/")
    
    extraction_results = []
    
    for f in vue_files:
        try:
            res = process_vue_file(f)
            extraction_results.append(res)
        except Exception as e:
            logger.error(f"Error processing {f}: {e}")
            
    out_dir = BASE / "task4"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "ui_extraction.json"
    
    # --- Write to MySQL Database ---
    try:
        conn = _get_connection(cfg)
        cur = conn.cursor()
        
        # Create a robust pathname map bypassing Windows slash and casing weirdness
        cur.execute("SELECT id, file_path FROM vue_files")
        file_map = {row[1].replace('\\', '/').lower(): row[0] for row in cur.fetchall()}
        
        elements_inserted = 0
        for res in extraction_results:
            clean_path = res.get("file", "").lower()
            file_id = None
            for db_path, fid in file_map.items():
                if db_path.endswith(clean_path):
                    file_id = fid
                    break
                    
            if not file_id:
                logger.warning(f"Could not link DB record for {res.get('file')}")
            
            if file_id:
                for btn in res["buttons"]:
                    cur.execute("INSERT INTO ui_extractions (file_id, element_category, text_content, css_class, text_type) VALUES (%s, %s, %s, %s, %s)", (file_id, "button", btn["text"], btn.get("class", ""), btn["type"]))
                    elements_inserted += 1
                for hdr in res["headers"]:
                    cur.execute("INSERT INTO ui_extractions (file_id, element_category, text_content, css_class, text_type) VALUES (%s, %s, %s, %s, %s)", (file_id, "header", hdr["text"], "", hdr["type"]))
                    elements_inserted += 1
                for vt in res["visibleTexts"]:
                    cur.execute("INSERT INTO ui_extractions (file_id, element_category, text_content, css_class, text_type) VALUES (%s, %s, %s, %s, %s)", (file_id, "visible_text", vt["text"], "", vt["type"]))
                    elements_inserted += 1
                    
        conn.commit()
        logger.info(f"Successfully wrote {elements_inserted} UI elements natively into MySQL database (ui_extractions)")
    except Exception as e:
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
        logger.error(f"Failed to write to MySQL db: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cur.close()
            conn.close()

    # Now drop raw_file_path specifically to preserve JSON schema exactly as required
    for res in extraction_results:
        res.pop("raw_file_path", None)
        
    final_json = {
        "uiExtraction": extraction_results
    }
    
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(final_json, out_f, indent=2)
        
    logger.info(f"Successfully wrote ui_extraction.json to {out_path}")

if __name__ == "__main__":
    main()
