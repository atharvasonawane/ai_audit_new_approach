import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
AUDIT_TOOL_DIR = BASE_DIR / "audit_tool"
TASK2_DIR = AUDIT_TOOL_DIR / "task2_audit"

# Add paths to sys.path so we can import internal modules easily
sys.path.insert(0, str(TASK2_DIR))

from db.db_writer import setup_schema, write_file_result, _get_connection


def main():
    # 1. Load config and DB credentials
    config_path = AUDIT_TOOL_DIR / "config" / "project_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Load environment variables
    load_dotenv(AUDIT_TOOL_DIR / ".env")
    if "db" not in cfg:
        cfg["db"] = {}
    cfg["db"]["host"] = os.getenv("MYSQL_HOST", cfg["db"].get("host", "localhost"))
    cfg["db"]["port"] = int(os.getenv("MYSQL_PORT", cfg["db"].get("port", 3306)))
    cfg["db"]["user"] = os.getenv("MYSQL_USER", cfg["db"].get("user", "root"))
    cfg["db"]["password"] = os.getenv("MYSQL_PASSWORD", cfg["db"].get("password", ""))
    cfg["db"]["database"] = os.getenv(
        "MYSQL_DATABASE", cfg["db"].get("database", "code_audit_db")
    )

    # Need a base_path so the path normalization in write_file_result doesn't complain
    cfg["base_path"] = str(BASE_DIR)

    print("=== Testing Database Schema Persistence ===")

    # 2. Run setup_schema() once
    print("1. Running first setup_schema()...")
    setup_schema(cfg)

    # 3. Insert a sample test record
    dummy_filepath = "persistence_test_dummy.vue"
    test_record = {
        "file": dummy_filepath,
        "module": "TestModule",
        "extracted_metrics": {"script_lines": 99},
        "api_calls": [],
        "flags_triggered": [],
        "confidence": "HIGH",
    }

    print("2. Inserting sample dummy record...")
    write_file_result(cfg, test_record)

    # 4. Run setup_schema() again (THE CRITICAL TEST)
    print("3. Running second setup_schema() to test persistence...")
    setup_schema(cfg)

    # 5. Query the database to check if the sample record still exists
    print("4. Querying the database to search for the dummy record...")
    conn = _get_connection(cfg)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM vue_files WHERE file_path LIKE %s", (f"%{dummy_filepath}%",)
    )
    row = cur.fetchone()

    # Cleanup the test data so we don't pollute the real database with a dummy
    if row:
        cur.execute("DELETE FROM vue_files WHERE id = %s", (row[0],))
        conn.commit()

    conn.close()

    # 6. Print the result
    print("=" * 45)
    if row:
        print("✅ TEST PASSED: The record persisted!")
    else:
        print("❌ TEST FAILED: The record was deleted!")
    print("=" * 45)


if __name__ == "__main__":
    main()
