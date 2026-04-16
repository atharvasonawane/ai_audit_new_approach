import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()
import sys

def check_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("ANALYZER_DB_HOST", "127.0.0.1"),
            user=os.getenv("ANALYZER_DB_USER", "root"),
            password=os.getenv("ANALYZER_DB_PASS", ""),
            database=os.getenv("ANALYZER_DB_NAME", "code_analyzer")
        )
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        print("Connected to code_analyzer database successfully.")
        print("Tables found:")
        for table in tables:
            print("-", table[0])
            
            # optionally, show columns for 'projects'
            cur.execute(f"DESCRIBE {table[0]}")
            cols = cur.fetchall()
            print(f"   Columns: {[col[0] for col in cols]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to code_analyzer: {e}")

if __name__ == "__main__":
    check_db()
