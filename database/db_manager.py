import sqlite3
import os
from config.settings import DB_PATH, log_info, log_error

def get_connection():
    """Returns a connection to the SQLite database with row formatting."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes database schema if tables do not exist and applies migrations."""
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
            status TEXT DEFAULT 'pending'
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
    
    # 5. Response Cache Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS response_cache (
            prompt TEXT PRIMARY KEY,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 6. Usage Analytics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            normalized TEXT NOT NULL,
            intent TEXT NOT NULL,
            capability TEXT NOT NULL,
            cache_hit INTEGER DEFAULT 0,
            llm_called INTEGER DEFAULT 0,
            latency_ms INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 7. Daily Statistics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_statistics (
            day TEXT PRIMARY KEY, -- Format: YYYY-MM-DD
            interactions INTEGER DEFAULT 0,
            llm_calls INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            avg_latency REAL DEFAULT 0.0
        )
    """)
    
    # 8. Active Days Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_days (
            day TEXT PRIMARY KEY -- Format: YYYY-MM-DD
        )
    """)
    
    # 9. Schema Info Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_info (
            version INTEGER PRIMARY KEY
        )
    """)
    
    # Check and apply migrations
    cursor.execute("SELECT version FROM schema_info")
    row = cursor.fetchone()
    
    target_version = 5
    current_version = 0
    if row:
        current_version = row["version"]
        
    if current_version < target_version:
        log_info(f"Running database migration: version {current_version} -> {target_version}")
        
        # Migrate reminders table completed column to status TEXT column
        try:
            cursor.execute("ALTER TABLE reminders ADD COLUMN status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        try:
            cursor.execute("UPDATE reminders SET status = 'completed' WHERE completed = 1")
        except sqlite3.OperationalError:
            pass
            
        cursor.execute("INSERT OR REPLACE INTO schema_info (version) VALUES (?)", (target_version,))
        conn.commit()
        log_info(f"Database migrated successfully to version {target_version}.")
    
    conn.commit()
    conn.close()
    log_info("Database tables verified.")

def run_maintenance():
    """Prunes completed/cancelled reminders older than 30 days and removes invalid entries."""
    from datetime import datetime, timedelta, timezone
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Naive UTC datetime for standard string comparison matching SQLite
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Clean up old completed/cancelled reminders
        cursor.execute(
            "DELETE FROM reminders WHERE (status = 'completed' OR status = 'cancelled') AND due_at <= ?",
            (cutoff_str,)
        )
        
        # 2. Drop invalid reminders
        cursor.execute("DELETE FROM reminders WHERE task = '' OR task IS NULL OR due_at IS NULL")
        
        conn.commit()
        log_info("Database maintenance completed successfully.")
    except sqlite3.Error as e:
        log_error(f"Database maintenance error: {e}")
    finally:
        conn.close()

# Auto-initialize database on import
init_db()
run_maintenance()
