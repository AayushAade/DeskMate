import sqlite3
import os
from config.settings import DB_PATH

def get_connection():
    """Returns a connection to the SQLite database with row formatting."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes database schema if tables do not exist."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Chat History Table (Episodic Memory storage)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL, -- 'user' or 'model'
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Preferences/Facts Table (Semantic Memory storage)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # 3. Reminders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            due_at DATETIME NOT NULL,
            completed INTEGER DEFAULT 0
        )
    """)
    
    # 4. Episodic Memory Summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("[DbManager] Database tables initialized successfully.")

# Auto-initialize database on import
init_db()
