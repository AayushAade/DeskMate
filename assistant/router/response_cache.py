import sqlite3
import re
from datetime import datetime, timezone
from database import db_manager
from config.settings import log_info, log_error, log_debug

def _normalize(prompt: str) -> str:
    """Normalizes the prompt for strict exact matching in <0.1ms."""
    q = prompt.lower().strip()
    q = re.sub(r'\s+', ' ', q)
    q = q.replace("?", "").replace("!", "").strip()
    return q

def get_cached_response(prompt: str) -> str | None:
    """
    Retrieves cached response from SQLite if present.
    Enforces a 10-minute TTL on weather-related prompts.
    """
    clean_p = _normalize(prompt)
    conn = db_manager.get_connection()
    res = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT response, timestamp FROM response_cache WHERE prompt = ?", (clean_p,))
        row = cursor.fetchone()
        
        if row:
            response_text = row["response"]
            timestamp_str = row["timestamp"]
            
            # Enforce 10-minute TTL for weather queries
            if clean_p.startswith("weather"):
                try:
                    db_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    # SQLite CURRENT_TIMESTAMP uses UTC
                    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    time_diff = (now_naive_utc - db_time).total_seconds()
                    if time_diff > 600:  # 10 minutes
                        log_info(f"Weather cache expired for: '{clean_p}' (aged {time_diff:.1f}s). Evicting.")
                        cursor.execute("DELETE FROM response_cache WHERE prompt = ?", (clean_p,))
                        conn.commit()
                        return None
                except Exception as e:
                    log_error(f"Error checking weather TTL: {e}")
                    
            res = response_text
    except sqlite3.Error as e:
        log_error(f"Error loading cached response: {e}")
    finally:
        conn.close()
    return res

def set_cached_response(prompt: str, response: str):
    """
    Saves a query response inside the SQLite response cache.
    Only caches LLM fallbacks, duckduckgo search queries, and Weather API queries.
    """
    clean_p = _normalize(prompt)
    if not clean_p or not response:
        return
        
    # Restrict caching: only cache LLM/Search/Weather queries
    # Do not cache local instant states (time, battery, clipboard, apps, calculator)
    should_cache = False
    
    # 1. Fallback / Search / Weather keywords
    if clean_p.startswith("weather") or clean_p.startswith("search"):
        should_cache = True
    elif not any(clean_p.startswith(p) for p in ["time", "battery", "clipboard", "open", "launch", "close", "run", "calculate"]):
        # It's a general LLM question fallback, cache it
        should_cache = True
        
    if not should_cache:
        return
        
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        # Explicitly write UTC timestamp matching SQLite's CURRENT_TIMESTAMP
        now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        now_utc_str = now_naive_utc.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT OR REPLACE INTO response_cache (prompt, response, timestamp) VALUES (?, ?, ?)",
            (clean_p, response, now_utc_str)
        )
        conn.commit()
    except sqlite3.Error as e:
        log_error(f"Error saving cached response: {e}")
    finally:
        conn.close()
