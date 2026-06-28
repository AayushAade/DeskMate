import sqlite3
from database import db_manager

def save_chat_message(session_id: str, sender: str, message: str):
    """Saves a single message to the chat history table."""
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (session_id, sender, message) VALUES (?, ?, ?)",
            (session_id, sender, message)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"[MemoryService] Error saving chat message: {e}")
    finally:
        conn.close()

def get_chat_history(session_id: str, limit: int = 20) -> list:
    """Retrieves recent chat history for a session."""
    conn = db_manager.get_connection()
    history = []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sender, message FROM chat_history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        )
        # Fetching in chronological order
        rows = cursor.fetchall()
        for row in reversed(rows):
            history.append({
                "role": "model" if row["sender"] == "model" else "user",
                "text": row["message"]
            })
    except sqlite3.Error as e:
        print(f"[MemoryService] Error loading chat history: {e}")
    finally:
        conn.close()
    return history

def set_preference(key: str, value: str):
    """Sets a semantic memory preference key-value pair."""
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"[MemoryService] Error setting preference: {e}")
    finally:
        conn.close()

def get_preference(key: str, default: str = None) -> str:
    """Retrieves a semantic memory preference value."""
    conn = db_manager.get_connection()
    val = default
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val = row["value"]
    except sqlite3.Error as e:
        print(f"[MemoryService] Error reading preference: {e}")
    finally:
        conn.close()
    return val
