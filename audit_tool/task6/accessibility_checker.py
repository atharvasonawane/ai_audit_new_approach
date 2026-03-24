"""
task6/accessibility_checker.py
==============================
Static AST analyzer for UI Accessibility & Usability Compliance Checks.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
BASE = Path(__file__).parent.parent
TASK2_BASE = BASE / "task2_audit"
CONFIG_PATH = str(BASE / "config" / "project_config.yaml")

sys.path.insert(0, str(TASK2_BASE))
import yaml
from extractors.vue_parser import parse_vue_file
from db.db_writer import _get_connection, write_accessibility_defect, _get_file_id

try:
    from tree_sitter import Parser
    from tree_sitter_language_pack import get_language as _get_ts_language
    CSS_LANG = _get_ts_language('css')
    _TS_CSS_AVAILABLE = True
except ImportError:
    _TS_CSS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s")
logger = logging.getLogger("accessibility_checker")

def get_node_tag_name(node, source_bytes):
    for child in node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for sub in child.children:
                if sub.type == "tag_name":
                    return source_bytes[sub.start_byte:sub.end_byte].decode("utf-8").strip().lower()
    return ""

def get_all_attributes(node, source_bytes) -> dict:
    attrs = {}
    for child in node.children:
        if child.type in ("start_tag", "self_closing_tag"):
            for attr in child.children:
                if attr.type == "attribute":
                    n = ""
                    v = ""
                    for sub in attr.children:
                        if sub.type == "attribute_name":
                            n = source_bytes[sub.start_byte:sub.end_byte].decode("utf-8").strip()
                        elif sub.type == "quoted_attribute_value":
                            for subval in sub.children:
                                if subval.type == "attribute_value":
                                    v = source_bytes[subval.start_byte:subval.end_byte].decode("utf-8")
                    if n:
                        attrs[n] = v
    return attrs

def get_text_content(node, source_bytes):
    texts = []
    def walk(n):
        if n.type == "text":
            val = source_bytes[n.start_byte:n.end_byte].decode("utf-8")
            if val.strip():
                texts.append(val.strip())
        elif n.type == "interpolation":
            texts.append(source_bytes[n.start_byte:n.end_byte].decode("utf-8").strip())
        else:
            for child in n.children:
                walk(child)
    walk(node)
    return " ".join(texts)

def has_icon_child(node, source_bytes):
    for child in node.children:
        if child.type in ("element", "self_closing_element"):
            tag = get_node_tag_name(child, source_bytes)
            if tag in ("i", "svg", "v-icon"):
                return True
            if has_icon_child(child, source_bytes):
                return True
    return False

def check_css_outline(style_text: str, file_id: int, file_path: str, module_name: str, cfg: dict, report_list: list):
    if not _TS_CSS_AVAILABLE or not style_text:
        return
    
    parser = Parser(CSS_LANG)
    source_bytes = style_text.encode("utf-8")
    tree = parser.parse(source_bytes)
    
    def walk_css(node):
        if node.type == "declaration":
            prop_name = ""
            prop_val = ""
            for child in node.children:
                if child.type == "property_name":
                    prop_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8").strip()
                elif child.type == "plain_value":
                    prop_val = source_bytes[child.start_byte:child.end_byte].decode("utf-8").strip()
            
            if prop_name == "outline" and prop_val in ("none", "0"):
                defect = {
                    "file_id": file_id,
                    "file_path": file_path,
                    "module": module_name,
                    "rule": "Rule 3.x",
                    "defect_type": "FOCUS_OUTLINE_REMOVED",
                    "element": "CSS outline",
                    "severity": "CRITICAL",
                    "line_number": node.start_point[0] + 1
                }
                write_accessibility_defect(cfg, defect)
                report_list.append(defect)
        for child in node.children:
            walk_css(child)
            
    walk_css(tree.root_node)

def process_vue_file(file_path, cfg, report_list):
    with open(file_path, "rb") as f:
        source_bytes = f.read()
    
    parsed = parse_vue_file(str(file_path))
    template_node = parsed.get("template_node")
    style_text = parsed.get("style_text")
    
    # Use the dynamic module name from cfg (calculated in run_audit.py)
    module_name = cfg.get("module", "unknown")
    
    norm_path = str(file_path).replace("\\", "/")
    
    # Determine clean_file_path: prefer src/-relative, else use full absolute path
    if "src/" in norm_path:
        clean_file_path = "src/" + norm_path.split("src/")[-1]
    else:
        clean_file_path = norm_path
    
    # Needs db file_id (we assume run_audit created vue_files)
    conn = _get_connection(cfg)
    cur = conn.cursor()
    file_id = 0
    try:
        cur.execute("SELECT id, file_path FROM vue_files")
        rows = cur.fetchall()
        
        # Build normalized suffix map
        norm_clean = clean_file_path.lower().replace("\\", "/")
        for row in rows:
            db_path_norm = row[1].replace("\\", "/").lower()
            # Match if either is a suffix of the other
            if db_path_norm.endswith(norm_clean) or norm_clean.endswith(db_path_norm.split("/src/")[-1] if "/src/" in db_path_norm else db_path_norm):
                file_id = row[0]
                break
    except Exception as e:
        logger.error(f"Error fetching file ID for {clean_file_path}: {e}")
    finally:
        cur.close()
        conn.close()
        
    if not file_id:
        logger.warning(f"Could not link DB record for {clean_file_path}")
        return

    # 1. Check style AST for outline: none
    if style_text:
        check_css_outline(style_text, file_id, clean_file_path, module_name, cfg, report_list)

    if not template_node:
        return
        
    # Preparation for HTML labels check
    label_fors = {}
    input_nodes = []
    
    def gather_labels_and_inputs(node):
        if node.type in ("element", "self_closing_element"):
            tag = get_node_tag_name(node, source_bytes)
            attrs = get_all_attributes(node, source_bytes)
            if tag == "label":
                text = get_text_content(node, source_bytes)
                if "for" in attrs:
                    label_fors[attrs["for"]] = text
            elif tag in ("input", "textarea", "select"):
                input_nodes.append((node, attrs))
                
        for child in node.children:
            gather_labels_and_inputs(child)
            
    gather_labels_and_inputs(template_node)

    def get_parent_label_text(node):
        curr = node.parent
        while curr:
            if curr.type in ("element", "self_closing_element"):
                t = get_node_tag_name(curr, source_bytes)
                if t == "label":
                    return get_text_content(curr, source_bytes)
            curr = curr.parent
        return ""
        
    def is_inside_tag(node, target_tag):
        curr = node.parent
        while curr:
            if curr.type in ("element", "self_closing_element"):
                t = get_node_tag_name(curr, source_bytes)
                if t == target_tag:
                    return True
            curr = curr.parent
        return False

    def emit_defect(rule, def_type, element, severity, node, extra=""):
        element_text = element
        if extra:
            element_text += f" | {extra}"
        d = {
            "file_id": file_id,
            "file_path": clean_file_path,
            "module": module_name,
            "rule": rule,
            "defect_type": def_type,
            "element": element_text,
            "severity": severity,
            "line_number": node.start_point[0] + 1
        }
        write_accessibility_defect(cfg, d)
        report_list.append(d)

    # Walk HTML AST for remaining checks
    def walk_template(node, has_aria_live_parent=False):
        attrs = {}
        tag = ""
        current_aria_live = has_aria_live_parent
        
        if node.type in ("element", "self_closing_element"):
            tag = get_node_tag_name(node, source_bytes)
            attrs = get_all_attributes(node, source_bytes)
            
            if "aria-live" in attrs:
                current_aria_live = True
                
            # Check 2: MISSING_ALT_TEXT
            if tag == "img":
                if "alt" not in attrs and ":alt" not in attrs:
                    emit_defect("Rule 3.4", "MISSING_ALT_TEXT", "<img ...>", "HIGH", node)
                    
            # Check 4: MISSING_ARIA_LABEL (icon buttons)
            if tag == "button":
                if has_icon_child(node, source_bytes):
                    text = get_text_content(node, source_bytes)
                    if not text and "aria-label" not in attrs and ":aria-label" not in attrs:
                        emit_defect("Rule 3.4", "MISSING_ARIA_LABEL", "<button> containing icon", "HIGH", node)
            
            # Check 6: DYNAMIC_CONTENT_NO_ARIA_LIVE
            if "v-if" in attrs or "v-show" in attrs:
                if not current_aria_live:
                    emit_defect("Rule 3.4", "DYNAMIC_CONTENT_NO_ARIA_LIVE", f"<{tag} v-if/v-show>", "MEDIUM", node)
                    
            # Check 8: NON_INTERACTIVE_WITH_CLICK
            if tag in ("div", "span", "p"):
                if "@click" in attrs or "v-on:click" in attrs:
                    has_role = attrs.get("role") == "button"
                    has_tabindex = "tabindex" in attrs or ":tabindex" in attrs
                    if not has_role or not has_tabindex:
                        extra = []
                        if not has_role: extra.append("missing role='button'")
                        if not has_tabindex: extra.append("missing tabindex='0'")
                        if "@keydown" not in attrs and "@keyup" not in attrs:
                            extra.append("missing keyboard event handling (@keydown/@keyup)")
                        emit_defect("Rule 3.2", "NON_INTERACTIVE_WITH_CLICK", f"<{tag} @click>", "HIGH", node, ", ".join(extra))
                        
            # Check 9: EMPTY_LINK
            if tag in ("a", "router-link"):
                href = attrs.get("href", attrs.get(":href", attrs.get("to", attrs.get(":to", ""))))
                no_href = "href" not in attrs and ":href" not in attrs and "to" not in attrs and ":to" not in attrs
                if no_href or href == "#" or href.startswith("javascript:void"):
                    if "aria-label" not in attrs and ":aria-label" not in attrs:
                        attr_str = f"href='{href}'" if not no_href else "missing href/to"
                        if tag == "router-link":
                            attr_str = f"to='{href}'" if not no_href else "missing to"
                        emit_defect("Rule 3.2", "EMPTY_LINK", f"<{tag} {attr_str}>", "MEDIUM", node)

        # Check inputs gathered (Checks 3 & 5)
        # Note: we do this by processing `input_nodes` outside the main walk to avoid duplicate emits,
        # but since we want the node object for the line number, we just check when tag is input
        if tag in ("input", "textarea"):
            input_id = attrs.get("id", "")
            has_label = False
            label_text = ""
            
            if input_id and input_id in label_fors:
                has_label = True
                label_text = label_fors[input_id]
            else:
                parent_text = get_parent_label_text(node)
                if parent_text:
                    has_label = True
                    label_text = parent_text
                
            has_placeholder = "placeholder" in attrs or ":placeholder" in attrs
            
            if not has_label:
                # UNLABELED_INPUT
                emit_defect("Rule 3.5", "UNLABELED_INPUT", f"<{tag} id='{input_id}'>", "HIGH", node)
                
                # PLACEHOLDER_USED_AS_LABEL
                if has_placeholder:
                    emit_defect("Rule 3.5", "PLACEHOLDER_USED_AS_LABEL", f"<{tag} placeholder>", "MEDIUM", node)
                    
            if "required" in attrs or ":required" in attrs:
                if not has_label or ("*" not in label_text and "required" not in label_text.lower()):
                    emit_defect("Rule 3.5", "REQUIRED_FIELD_NOT_MARKED", f"<{tag} required> (missing visual * in label)", "MEDIUM", node)

        for child in node.children:
            walk_template(child, current_aria_live)
            
    walk_template(template_node)

def main(cfg=None):
    if not cfg:
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
    base_dir = BASE / Path(base_path)
    components_dir = base_dir / "components"
    views_dir = base_dir / "views"
    
    vue_files = []
    if components_dir.exists():
        vue_files.extend(list(components_dir.rglob("*.vue")))
    if views_dir.exists():
        vue_files.extend(list(views_dir.rglob("*.vue")))
        
    sample_admin = BASE.parent / "adminLogin.vue"
    if sample_admin.exists() and sample_admin not in vue_files:
        vue_files.append(sample_admin)
        
    logger.info(f"Found {len(vue_files)} .vue files for Accessibility Checker")
    
    report_list = []
    
    for f in vue_files:
        try:
            process_vue_file(f, cfg, report_list)
        except Exception as e:
            logger.error(f"Error processing {f} for accessibility: {e}")
            
    # Export JSON
    out_dir = BASE / "task6"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "accessibility_report.json"
    
    final_json = {
        "accessibility_defects": report_list,
        "total_defects": len(report_list),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(final_json, out_f, indent=2)
        
    logger.info(f"Accessibility evaluation complete. Found {len(report_list)} defects.")
    logger.info(f"Wrote report to {out_path}")

if __name__ == "__main__":
    main()
