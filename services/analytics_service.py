import sqlite3
from datetime import datetime
from database import db_manager

def record_active_day():
    """Inserts the current date into active_days if not already present."""
    day_str = datetime.now().strftime('%Y-%m-%d')
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO active_days (day) VALUES (?)", (day_str,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[Analytics] Error saving active day: {e}")
    finally:
        conn.close()

def log_interaction(query: str, normalized: str, intent: str, capability: str, cache_hit: bool, llm_called: bool, latency_ms: int):
    """
    Logs raw interaction telemetry, prunes log records to 5,000 rows, 
    and updates daily statistics in SQLite.
    """
    # 1. Ensure we record active day
    record_active_day()
    
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        
        # 2. Insert raw record
        cursor.execute(
            """
            INSERT INTO usage_analytics 
            (query, normalized, intent, capability, cache_hit, llm_called, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (query, normalized, intent, capability, 1 if cache_hit else 0, 1 if llm_called else 0, latency_ms)
        )
        
        # 3. Prune old records (Limit to 5000)
        cursor.execute(
            """
            DELETE FROM usage_analytics WHERE id NOT IN (
                SELECT id FROM usage_analytics ORDER BY id DESC LIMIT 5000
            )
            """
        )
        
        # 4. Update daily statistics
        day_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT interactions, llm_calls, cache_hits, avg_latency FROM daily_statistics WHERE day = ?", (day_str,))
        row = cursor.fetchone()
        
        c_hit_val = 1 if cache_hit else 0
        llm_val = 1 if llm_called else 0
        
        if row:
            # Update values
            new_interactions = row["interactions"] + 1
            new_llm = row["llm_calls"] + llm_val
            new_hits = row["cache_hits"] + c_hit_val
            
            # Recalculate average latency
            total_lat = (row["avg_latency"] * row["interactions"]) + latency_ms
            new_avg = total_lat / new_interactions
            
            cursor.execute(
                """
                UPDATE daily_statistics 
                SET interactions = ?, llm_calls = ?, cache_hits = ?, avg_latency = ?
                WHERE day = ?
                """,
                (new_interactions, new_llm, new_hits, new_avg, day_str)
            )
        else:
            # Insert first entry of day
            cursor.execute(
                """
                INSERT INTO daily_statistics (day, interactions, llm_calls, cache_hits, avg_latency)
                VALUES (?, 1, ?, ?, ?)
                """,
                (day_str, llm_val, c_hit_val, float(latency_ms))
            )
            
        conn.commit()
    except sqlite3.Error as e:
        print(f"[Analytics] Error logging interaction: {e}")
    finally:
        conn.close()

def get_aggregate_stats() -> dict:
    """Computes Mochi's aggregate statistics from SQLite usage tables."""
    conn = db_manager.get_connection()
    stats = {
        "total_interactions": 0,
        "local_hits_percentage": 0.0,
        "llm_fallback_percentage": 0.0,
        "cache_hits_percentage": 0.0,
        "avg_latency": 0.0,
        "top_capabilities": [],
        "cap_latencies": {}
    }
    
    try:
        cursor = conn.cursor()
        
        # Get total interactions
        cursor.execute("SELECT COUNT(*) as count FROM usage_analytics")
        total = cursor.fetchone()["count"]
        stats["total_interactions"] = total
        
        if total > 0:
            # LLM fallback count
            cursor.execute("SELECT COUNT(*) as count FROM usage_analytics WHERE capability = 'llm'")
            llm_count = cursor.fetchone()["count"]
            stats["llm_fallback_percentage"] = (llm_count / total) * 100.0
            stats["local_hits_percentage"] = ((total - llm_count) / total) * 100.0
            
            # Cache hits count
            cursor.execute("SELECT COUNT(*) as count FROM usage_analytics WHERE cache_hit = 1")
            cache_hits = cursor.fetchone()["count"]
            stats["cache_hits_percentage"] = (cache_hits / total) * 100.0
            
            # Avg latency
            cursor.execute("SELECT AVG(latency_ms) as avg_lat FROM usage_analytics")
            stats["avg_latency"] = cursor.fetchone()["avg_lat"] or 0.0
            
            # Top 5 capabilities
            cursor.execute("SELECT capability, COUNT(*) as count FROM usage_analytics GROUP BY capability ORDER BY count DESC LIMIT 5")
            stats["top_capabilities"] = [{"capability": r["capability"], "count": r["count"]} for r in cursor.fetchall()]
            
            # Avg latency per capability
            cursor.execute("SELECT capability, AVG(latency_ms) as avg_lat FROM usage_analytics GROUP BY capability")
            stats["cap_latencies"] = {r["capability"]: r["avg_lat"] for r in cursor.fetchall()}
            
    except sqlite3.Error as e:
        print(f"[Analytics] Error retrieving statistics: {e}")
    finally:
        conn.close()
    return stats
