import sqlite3
import os

OPS_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "ops_database.db")

def init_ops_db():
    """
    Initializes and seeds a local SQLite database for Text2SQL pipelines.
    """
    os.makedirs(os.path.dirname(OPS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(OPS_DB_PATH)
    cursor = conn.cursor()
    
    # Create metadata tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles_meta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        source TEXT,
        scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        category TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        query_count INTEGER DEFAULT 0,
        last_query TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_status (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Seed default data if empty
    cursor.execute("SELECT COUNT(*) FROM articles_meta")
    if cursor.fetchone()[0] == 0:
        seed_data = [
            ("India Launches New Defense Satellites", "https://example.com/satellite", "Indian Express", "Defense"),
            ("Reserve Bank of India Keeps Repo Rate Steady at 6.5%", "https://example.com/repo", "The Hindu", "Economy"),
            ("National Health Mission Expansion Approved by Cabinet", "https://example.com/health", "The Hindu", "Policy"),
            ("ISRO Announces Gaganyaan Mission Trajectory Tests", "https://example.com/gaganyaan", "Indian Express", "Science"),
            ("Cabinet Approves New Educational Exchange Treaties", "https://example.com/edu", "The Hindu", "Education")
        ]
        cursor.executemany("""
        INSERT INTO articles_meta (title, url, source, category) VALUES (?, ?, ?, ?)
        """, seed_data)
        
    cursor.execute("SELECT COUNT(*) FROM user_analytics")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO user_analytics (user_id, query_count, last_query) 
        VALUES ('student_101', 42, 'What is repo rate?')
        """)
        
    cursor.execute("SELECT COUNT(*) FROM system_status")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_status (key, value) VALUES ('pipeline_status', 'HEALTHY')")
        cursor.execute("INSERT INTO system_status (key, value) VALUES ('pinecone_sync', 'SYNCHRONIZED')")
        
    conn.commit()
    conn.close()

def execute_sql(sql: str) -> list[dict]:
    """
    Executes a SELECT SQL query against the operations database.
    Returns list of dicts.
    """
    conn = sqlite3.connect(OPS_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))
        return result
    except Exception as e:
        print(f"SQL Execution error: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

# Auto-initialize on import
init_ops_db()
