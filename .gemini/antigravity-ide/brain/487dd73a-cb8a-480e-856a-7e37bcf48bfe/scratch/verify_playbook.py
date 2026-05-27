import urllib.request
import json
import sqlite3
from pathlib import Path

def run_chat_query(run_id, message, label):
    print(f"\n========================================\n{label}\nMessage: '{message}'\n========================================")
    payload = {
        "run_id": run_id,
        "message": message,
        "history": []
    }
    req = urllib.request.Request(
        "http://localhost:5000/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST"
    )
    try:
        response = urllib.request.urlopen(req, timeout=15)
        for line in response:
            line_decoded = line.decode("utf-8").strip()
            if line_decoded.startswith("data:"):
                data_part = line_decoded[5:].strip()
                if data_part == "[DONE]":
                    print("[DONE]")
                    break
                try:
                    data_json = json.loads(data_part)
                    if "token" in data_json:
                        print(data_json["token"], end="", flush=True)
                    elif "error" in data_json:
                        print(f"\n[Error: {data_json['error']}]")
                except Exception as e:
                    pass
        print()
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    db_path = Path("audit_history.db")
    test_run_id = 5
    
    # 1. Fetch a real file path from the database to use as a substring test
    test_substring = "RoleMgt"  # default fallback
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute("SELECT file_path FROM vue_files WHERE run_id = ? LIMIT 1", (test_run_id,)).fetchone()
            if row:
                full_path = row[0]
                import os
                basename = os.path.basename(full_path)
                test_substring = os.path.splitext(basename)[0]
                print(f"Found real database file: '{full_path}' -> substring to test: '{test_substring}'")
            conn.close()
        except Exception as e:
            print(f"Error reading SQLite database: {e}")
            
    # Test 1: Selected Run Context
    run_chat_query(test_run_id, "Which audit scan is currently selected?", "Test 1: Selected Run Context")
    
    # Test 2: Substring Matching on Target Component
    run_chat_query(test_run_id, f"tell me about file {test_substring}", "Test 2: Substring Matching")
