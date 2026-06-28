import sqlite3
from database import db_manager

def save_fact(key: str, value: str):
    """Saves a durable user fact in SQLite."""
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"[SemanticMemory] Error saving fact '{key}': {e}")
    finally:
        conn.close()

def get_fact(key: str, default: str = None) -> str:
    """Retrieves a durable user fact from SQLite."""
    conn = db_manager.get_connection()
    val = default
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val = row["value"]
    except sqlite3.Error as e:
        print(f"[SemanticMemory] Error reading fact '{key}': {e}")
    finally:
        conn.close()
    return val

def get_all_facts() -> dict:
    """Retrieves all stored facts as a key-value dictionary."""
    conn = db_manager.get_connection()
    facts = {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM preferences")
        rows = cursor.fetchall()
        for row in rows:
            facts[row["key"]] = row["value"]
    except sqlite3.Error as e:
        print(f"[SemanticMemory] Error reading all facts: {e}")
    finally:
        conn.close()
    return facts

def delete_fact(key: str):
    """Deletes a fact from semantic memory."""
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preferences WHERE key = ?", (key,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[SemanticMemory] Error deleting fact '{key}': {e}")
    finally:
        conn.close()
