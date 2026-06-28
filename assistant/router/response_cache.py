import sqlite3
import re
from database import db_manager

def _normalize(prompt: str) -> str:
    """Normalizes the prompt for strict exact matching in <0.1ms."""
    q = prompt.lower().strip()
    q = re.sub(r'\s+', ' ', q)
    q = q.replace("?", "").replace("!", "").strip()
    return q

def get_cached_response(prompt: str) -> str | None:
    """Retrieves cached response from SQLite if present."""
    clean_p = _normalize(prompt)
    conn = db_manager.get_connection()
    res = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM response_cache WHERE prompt = ?", (clean_p,))
        row = cursor.fetchone()
        if row:
            res = row["response"]
    except sqlite3.Error as e:
        print(f"[ResponseCache] Error loading cached response: {e}")
    finally:
        conn.close()
    return res

def set_cached_response(prompt: str, response: str):
    """Saves a query response inside the SQLite response cache."""
    clean_p = _normalize(prompt)
    if not clean_p or not response:
        return
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO response_cache (prompt, response) VALUES (?, ?)",
            (clean_p, response)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ResponseCache] Error saving cached response: {e}")
    finally:
        conn.close()
