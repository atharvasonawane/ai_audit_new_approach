import sqlite3
import sys
from pathlib import Path

def main():
    db_path = Path("audit_tool/audit_history.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # 1. Check vue_files
        print("\n" + "="*80)
        print("STAGE 3: EXTRACTED FILES & METRICS")
        print("="*80)
        cursor = conn.execute("SELECT file_path, script_lines, methods, api_total FROM vue_files")
        files = cursor.fetchall()
        for f in files:
            print(f"- {f['file_path']} (Lines: {f['script_lines']}, Methods: {f['methods']}, APIs: {f['api_total']})")
            
        # 2. Check Stage 5
        print("\n" + "="*80)
        print("STAGE 5: AI DEPENDENCY ISSUES (MACRO-ARCHITECTURE)")
        print("="*80)
        cursor = conn.execute("SELECT file_path, issue_category, severity FROM ai_issues WHERE phase='dependency'")
        dep_issues = cursor.fetchall()
        for i in dep_issues:
            print(f"[{i['severity']}] {i['issue_category']} -> {i['file_path']}")
            
        # 3. Check Stage 6
        print("\n" + "="*80)
        print("STAGE 6: AI PER-FILE ISSUES (MICRO-ARCHITECTURE)")
        print("="*80)
        cursor = conn.execute("SELECT file_path, issue_category, severity, line_number FROM ai_issues WHERE phase='per_file'")
        arch_issues = cursor.fetchall()
        for i in arch_issues:
            print(f"[{i['severity']}] {i['issue_category']} -> {i['file_path']} (Line {i['line_number']})")
            
        print("\n" + "="*80)
        print(f"PIPELINE SUMMARY: {len(files)} files scanned | {len(dep_issues)} dependency issues | {len(arch_issues)} architectural issues")
        print("="*80 + "\n")

        # 4. Check Stage 7
        print("\n" + "="*80)
        print("STAGE 7: AI ARCHITECTURE SYNTHESIS (EXECUTIVE REPORT)")
        print("="*80)
        cursor = conn.execute("SELECT synthesis_text FROM audit_runs WHERE current_phase='report' AND status='complete' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row and row['synthesis_text']:
            print("[🟢 SUCCESS] Synthesis text found in audit_runs!")
            print("Preview:\n" + row['synthesis_text'][:300] + "...\n")
        else:
            print("[🔴 ERROR] No synthesis text found.\n")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
