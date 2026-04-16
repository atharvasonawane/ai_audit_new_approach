import os
from dotenv import load_dotenv
load_dotenv()
import sys
import json
import yaml
import mysql.connector

# Base config locator
BASE_DIR = r"c:\Users\Atharvaso\Desktop\final_approach"
CONFIG_YAML = os.path.join(BASE_DIR, "audit_tool", "config", "project_config.yaml")
REPORTS_DIR = os.path.join(BASE_DIR, "audit_tool")

def main():
    # Read configuration dynamically
    if not os.path.exists(CONFIG_YAML):
        print(f"Error: Config file not found at {CONFIG_YAML}")
        sys.exit(1)
        
    with open(CONFIG_YAML, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    db_config = config.get("db", {})
    project_name = config.get("project", "default_project")
    
    # We enforce forward slashes for cross-platform processing
    base_path = config.get("base_path", "").replace('\\', '/')
    
    # Connect to the code_analyzer database specifically
    try:
        conn = mysql.connector.connect(
            host=os.getenv("ANALYZER_DB_HOST", "127.0.0.1"),
            user=os.getenv("ANALYZER_DB_USER", "root"),
            password=os.getenv("ANALYZER_DB_PASS", ""),
            database=os.getenv("ANALYZER_DB_NAME", "code_analyzer")
        )
    except Exception as e:
        print(f"Database Connection Error: {e}")
        sys.exit(1)

    cur = conn.cursor(dictionary=True)
    
    print(f"Starting dynamic data ingestion for project '{project_name}'...")
    print("Clearing existing data...")
    
    # Disable foreign key checks to allow truncating
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    tables_to_clear = [
        'rule_violations', 'flags', 'ui_nodes', 'apis', 'metrics', 
        'components', 'files', 'folders', 'projects', 'rules'
    ]
    for table in tables_to_clear:
        cur.execute(f"TRUNCATE TABLE {table}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

    # --- 1. Create Dynamic Project ---
    cur.execute("INSERT INTO projects (project_name, description) VALUES (%s, %s)",
                (project_name, f"Loaded using base path: {base_path}"))
    project_id = cur.lastrowid
    
    print(f"Created project: {project_name} (ID: {project_id})")

    folder_map = {} # path -> folder_id
    file_map = {}   # filepath -> file_id
    rule_map = {}   # rule name -> rule_id

    def normalize_path(filepath):
        # Dynamically isolates relative paths strictly based on configured base_path
        normalized = filepath.replace('\\', '/')
        if base_path and normalized.lower().startswith(base_path.lower()):
            normalized = normalized[len(base_path):].lstrip('/')
        # Strips out any loose Windows drive references if the base_path wasn't successfully removed
        elif ':/' in normalized:
            normalized = normalized.split(':/', 1)[-1].lstrip('/')
        return normalized
    
    def get_or_create_folder(folder_path):
        if not folder_path:
            return None
        if folder_path in folder_map:
            return folder_map[folder_path]
            
        # Recursive resolution of parent folder
        parent_path = os.path.dirname(folder_path)
        parent_id = None
        if parent_path and parent_path != folder_path:
            parent_id = get_or_create_folder(parent_path)
            
        folder_name = os.path.basename(folder_path) or folder_path
        cur.execute("INSERT INTO folders (project_id, folder_name, folder_path, parent_id) VALUES (%s, %s, %s, %s)",
                    (project_id, folder_name, folder_path, parent_id))
        folder_id = cur.lastrowid
        folder_map[folder_path] = folder_id
        return folder_id

    def get_or_create_rule(rule_name, category, severity, extract=''):
        if rule_name in rule_map:
            return rule_map[rule_name]
        
        cur.execute("""
            INSERT INTO rules (rule_name, category, description, severity, deduction)
            VALUES (%s, %s, %s, %s, 1.0)
        """, (rule_name, category, extract, severity))
        rule_id = cur.lastrowid
        rule_map[rule_name] = rule_id
        return rule_id

    # Dynamic Report Paths
    complexity_json = os.path.join(REPORTS_DIR, "task3", "component_complexity.json")
    issue_report_json = os.path.join(REPORTS_DIR, "task7", "issue_report.json")
    a11y_json = os.path.join(REPORTS_DIR, "task6", "accessibility_report.json")
    ui_extraction_json = os.path.join(REPORTS_DIR, "task4", "ui_extraction.json")
    ui_consistency_json = os.path.join(REPORTS_DIR, "task5", "ui_consistency_report.json")

    component_map = {}  # file_id -> component_id (for linking ui_nodes)

    # --- 2. Load Component Complexity (Files and Metrics) ---
    comp_data = {}
    if os.path.exists(complexity_json):
        print(f"Loading {complexity_json}...")
        with open(complexity_json, 'r', encoding='utf-8') as f:
            comp_data = json.load(f)
            
        for item in comp_data.get('componentComplexity', []):
            filepath = item.get('file', '')

            # Determine folder paths
            normalized_path = normalize_path(filepath)
            folder_path = os.path.dirname(normalized_path)
            folder_id = get_or_create_folder(folder_path)

            file_name = os.path.basename(normalized_path)
            _, ext = os.path.splitext(file_name)

            loc = item.get('lines', 0)

            # Ensure we don't insert duplicate file paths
            if filepath not in file_map:
                cur.execute("""
                    INSERT INTO files (project_id, folder_id, file_name, file_path, extension, loc)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (project_id, folder_id, file_name, filepath, ext, loc))
                file_id = cur.lastrowid
                file_map[filepath] = file_id

                # create component
                cur.execute("""
                    INSERT INTO components (file_id, component_name, component_type)
                    VALUES (%s, %s, %s)
                """, (file_id, file_name, 'VIEW'))
                component_map[file_id] = cur.lastrowid

                # Insert Metrics
                metrics_to_add = [
                    ('lines', item.get('lines', 0)),
                    ('methods', item.get('methods', 0)),
                    ('computed', item.get('computed', 0)),
                    ('watchers', item.get('watchers', 0)),
                    ('templateLines', item.get('templateLines', 0)),
                    ('childComponents', item.get('childComponents', 0))
                ]
                for m_name, m_val in metrics_to_add:
                    cur.execute("""
                        INSERT INTO metrics (entity_type, entity_id, metric_name, metric_value)
                        VALUES (%s, %s, %s, %s)
                    """, ('FILE', file_id, m_name, float(m_val)))

    # --- 3. Load Issue Report (Flags and A11y Rules combined) ---
    issue_data = {}
    if os.path.exists(issue_report_json):
        print(f"Loading {issue_report_json}...")
        with open(issue_report_json, 'r', encoding='utf-8') as f:
            issue_data = json.load(f)
        
    for f_data in issue_data.get('files', []):
        filepath = f_data.get('file', '')
        
        # some paths might not be in complexity report
        if filepath not in file_map:
            normalized_path = normalize_path(filepath)
            folder_path = os.path.dirname(normalized_path)
            folder_id = get_or_create_folder(folder_path)
            file_name = os.path.basename(normalized_path)
            _, ext = os.path.splitext(file_name)
            
            cur.execute("""
                INSERT INTO files (project_id, folder_id, file_name, file_path, extension, loc)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (project_id, folder_id, file_name, filepath, ext))
            file_id = cur.lastrowid
            file_map[filepath] = file_id
        else:
            file_id = file_map[filepath]

        for issue in f_data.get('issues', []):
            i_type = issue.get('type')
            
            if i_type == 'FLAG':
                rule_name = issue.get('name')
                category = issue.get('category')
                
                rule_id = get_or_create_rule(rule_name, category, 'MEDIUM', 'Extracted from JSON Flag')
                
                cur.execute("""
                    INSERT INTO flags (entity_type, entity_id, rule_id, flag_name, severity, details)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('FILE', file_id, rule_id, rule_name, 'MEDIUM', json.dumps(issue)))
            
            elif i_type in ['UI_DEFECT', 'A11Y_DEFECT']:
                defect_type = issue.get('defect_type')
                severity = issue.get('severity', 'HIGH')
                rule_mapped = issue.get('rule', 'UI_DEFECT_RULE')
                
                rule_id = get_or_create_rule(defect_type, i_type, severity, rule_mapped)
                
                # Rule Violations
                cur.execute("""
                    INSERT INTO rule_violations (rule_id, entity_type, entity_id, status, message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (rule_id, 'FILE', file_id, 'FAILED', issue.get('element', '') or issue.get('snippet', ''), json.dumps(issue)))

    # --- 4. Load A11y Defect report specifically ---
    a11y_data = {}
    if os.path.exists(a11y_json):
        print(f"Loading {a11y_json}...")
        with open(a11y_json, 'r', encoding='utf-8') as f:
            a11y_data = json.load(f)
        
    for item in a11y_data.get('accessibility_defects', []):
        filepath = item.get('file_path', '')
        
        if filepath not in file_map:
            # skipping isolated unmapped files for now, or we can insert
            normalized_path = normalize_path(filepath)
            folder_path = os.path.dirname(normalized_path)
            folder_id = get_or_create_folder(folder_path)
            file_name = os.path.basename(normalized_path)
            _, ext = os.path.splitext(file_name)
            
            cur.execute("""
                INSERT INTO files (project_id, folder_id, file_name, file_path, extension, loc)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (project_id, folder_id, file_name, filepath, ext))
            file_id = cur.lastrowid
            file_map[filepath] = file_id
        else:
            file_id = file_map[filepath]

        rule_name = item.get('defect_type')
        severity = item.get('severity', 'HIGH')
        rule_details = item.get('rule')
        
        rule_id = get_or_create_rule(rule_name, 'ACCESSIBILITY', severity, rule_details)
        
        cur.execute("""
            INSERT INTO rule_violations (rule_id, entity_type, entity_id, status, message, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (rule_id, 'FILE', file_id, 'FAILED', item.get('element', ''), json.dumps(item)))

    # --- 5. Load UI Extraction (Task 4 → ui_nodes) ---
    ui_node_count = 0
    ui_data = {}
    if os.path.exists(ui_extraction_json):
        print(f"Loading {ui_extraction_json}...")
        with open(ui_extraction_json, 'r', encoding='utf-8') as f:
            ui_data = json.load(f)

    for item in ui_data.get('uiExtraction', []):
        filepath = item.get('file', '')
        file_id = file_map.get(filepath)
        if not file_id:
            continue

        comp_id = component_map.get(file_id)
        if not comp_id:
            continue

        # Load buttons
        for btn in item.get('buttons', []):
            is_dynamic = 1 if btn.get('type') == 'i18n' else 0
            cur.execute("""
                INSERT INTO ui_nodes (component_id, tag_name, text_value, css_class, attributes, is_dynamic)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (comp_id, 'button', btn.get('text', ''), btn.get('class', ''),
                  json.dumps(btn), is_dynamic))
            ui_node_count += 1

        # Load headers
        for hdr in item.get('headers', []):
            is_dynamic = 1 if hdr.get('type') == 'i18n' else 0
            cur.execute("""
                INSERT INTO ui_nodes (component_id, tag_name, text_value, css_class, attributes, is_dynamic)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (comp_id, 'header', hdr.get('text', ''), '',
                  json.dumps(hdr), is_dynamic))
            ui_node_count += 1

        # Load visible texts
        for txt in item.get('visibleTexts', []):
            is_dynamic = 1 if txt.get('type') == 'i18n' else 0
            cur.execute("""
                INSERT INTO ui_nodes (component_id, tag_name, text_value, css_class, attributes, is_dynamic)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (comp_id, 'text', txt.get('text', ''), '',
                  json.dumps(txt), is_dynamic))
            ui_node_count += 1

    print(f"  Loaded {ui_node_count} UI nodes from Task 4.")

    # --- 6. Load UI Consistency / Spell Defects (Task 5 → rule_violations) ---
    spell_count = 0
    consistency_data = {}
    if os.path.exists(ui_consistency_json):
        print(f"Loading {ui_consistency_json}...")
        with open(ui_consistency_json, 'r', encoding='utf-8') as f:
            consistency_data = json.load(f)

    for item in consistency_data.get('uiConsistency', []):
        filepath = item.get('file', '')
        file_id = file_map.get(filepath)
        if not file_id:
            continue

        for defect in item.get('defects', []):
            defect_type = defect.get('defect_type', 'UNKNOWN')
            severity = defect.get('severity', 'LOW')
            category = 'SPELLING' if defect_type == 'SPELLING' else 'UI_CONSISTENCY'

            rule_id = get_or_create_rule(defect_type, category, severity,
                                         f"{defect.get('element_type', '')}: {defect.get('trigger_text', '')}")

            message = f"{defect.get('trigger_text', '')} → {defect.get('expected_text', '')}"
            cur.execute("""
                INSERT INTO rule_violations (rule_id, entity_type, entity_id, status, message, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (rule_id, 'FILE', file_id, 'FAILED', message, json.dumps(defect)))
            spell_count += 1

        # Also store consistency_score as a metric
        score = item.get('consistency_score')
        if score is not None:
            cur.execute("""
                INSERT INTO metrics (entity_type, entity_id, metric_name, metric_value)
                VALUES (%s, %s, %s, %s)
            """, ('FILE', file_id, 'consistency_score', float(score)))

    print(f"  Loaded {spell_count} spelling/consistency defects from Task 5.")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n{'='*50}")
    print(f"Data ingestion completed!")
    print(f"  Files:            {len(file_map)}")
    print(f"  UI Nodes:         {ui_node_count}")
    print(f"  Spell Defects:    {spell_count}")
    print(f"  Rules Created:    {len(rule_map)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
