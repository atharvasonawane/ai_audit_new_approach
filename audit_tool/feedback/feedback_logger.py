import mysql.connector
import json
import logging

logger = logging.getLogger(__name__)

def _get_connection(cfg: dict):
    """Helper to establish a connection using the provided config."""
    db = cfg["db"]
    return mysql.connector.connect(
        host=db.get("host", "localhost"),
        port=int(db.get("port", 3306)),
        user=db["user"],
        password=db["password"],
        database=db["database"]
    )

def create_feedback_table(cfg: dict):
    """Creates the librarian_feedback table if it doesn't already exist."""
    query = """
    CREATE TABLE IF NOT EXISTS librarian_feedback (
      id INT AUTO_INCREMENT PRIMARY KEY,
      query TEXT NOT NULL,
      file_path VARCHAR(500),
      tool_used VARCHAR(100),
      agent_answer TEXT,
      verifier_result TEXT,
      was_correct TINYINT(1),
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    try:
        conn = _get_connection(cfg)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
    except Exception as e:
        logger.error(f"[feedback_logger] Failed to create feedback table: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

def log_feedback(cfg, query, file_path, tool_used, agent_answer, verifier_result, was_correct):
    """Inserts a single feedback record into the database."""
    if isinstance(verifier_result, dict):
        verifier_result = json.dumps(verifier_result)
        
    sql = """
    INSERT INTO librarian_feedback 
    (query, file_path, tool_used, agent_answer, verifier_result, was_correct) 
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    # Parameterized values to prevent SQL injection
    vals = (query, file_path, tool_used, agent_answer, verifier_result, int(was_correct))
    
    try:
        conn = _get_connection(cfg)
        cursor = conn.cursor()
        cursor.execute(sql, vals)
        conn.commit()
        print("[FEEDBACK] Successfully logged wrong answer to MySQL.")
    except Exception as e:
        logger.error(f"[feedback_logger] Failed to log feedback: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()