import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

def verify():
    conn = mysql.connector.connect(
        host=os.getenv("ANALYZER_DB_HOST", "127.0.0.1"),
        user=os.getenv("ANALYZER_DB_USER", "root"),
        password=os.getenv("ANALYZER_DB_PASS", ""),
        database=os.getenv("ANALYZER_DB_NAME", "code_analyzer")
    )
    cur = conn.cursor()
    tables = ['projects', 'folders', 'files', 'components', 'metrics', 'flags', 'rules', 'rule_violations']
    print("Database summary:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"{t}: {count} rows")
    cur.close()
    conn.close()

if __name__ == "__main__":
    verify()
