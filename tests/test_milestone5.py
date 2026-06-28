import unittest
import os
import time
from datetime import datetime, timedelta, timezone
from config import settings

# Point database to a test database during testing to prevent polluting actual database
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from assistant.state.state_manager import state_manager
from assistant.router import response_cache
from services import analytics_service

class TestMilestone5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_manager.init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def setUp(self):
        # Reset state manager
        state_manager.mood = "Relaxed"
        state_manager.emotion = None
        state_manager.affection_level = "Stranger"
        state_manager.energy = 80
        state_manager.focus_mode = False
        state_manager.idle_seconds = 0
        state_manager.is_typing = False
        
        # Clear database analytics
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM usage_analytics")
        conn.execute("DELETE FROM daily_statistics")
        conn.execute("DELETE FROM active_days")
        conn.execute("DELETE FROM response_cache")
        conn.commit()
        conn.close()

    def test_state_transitions_mood_emotion(self):
        # Initial mood/emotion
        self.assertEqual(state_manager.mood, "Relaxed")
        self.assertIsNone(state_manager.emotion)
        
        # Charger connected -> Excited emotion
        state_manager.handle_event("CHARGER_CONNECTED")
        self.assertEqual(state_manager.emotion, "Excited")
        self.assertEqual(state_manager.mood, "Relaxed")  # mood remains unchanged
        self.assertEqual(state_manager.emotion_timer, 30)
        
        # Calculation completed -> Focused mood, Happy emotion
        state_manager.handle_event("CALCULATION_COMPLETED")
        self.assertEqual(state_manager.mood, "Focused")
        self.assertEqual(state_manager.emotion, "Happy")
        self.assertEqual(state_manager.emotion_timer, 15)
        
        # Tick decrements emotion timer
        state_manager.handle_event("TICK", {"idle_seconds": 0, "is_typing": False})
        self.assertEqual(state_manager.emotion_timer, 14)
        
        # Fast-forward emotion timeout
        state_manager.emotion_timer = 1
        state_manager.handle_event("TICK", {"idle_seconds": 0, "is_typing": False})
        self.assertIsNone(state_manager.emotion)  # Reverts to None (long-term Focused mood plays)
        self.assertEqual(state_manager.mood, "Focused")

    def test_analytics_pruning_and_aggregates(self):
        # Insert raw interactions
        for i in range(10):
            analytics_service.log_interaction(
                query="test prompt",
                normalized="test prompt",
                intent="general",
                capability="calculator",
                cache_hit=False,
                llm_called=False,
                latency_ms=10
            )
            
        stats = analytics_service.get_aggregate_stats()
        self.assertEqual(stats["total_interactions"], 10)
        self.assertEqual(stats["local_hits_percentage"], 100.0)
        self.assertEqual(stats["llm_fallback_percentage"], 0.0)
        self.assertEqual(stats["avg_latency"], 10.0)
        
        # Test table pruning boundary (simulate 5005 rows, check it clips to 5000)
        # To avoid running a slow loop of 5000 inserts, we test the prune directly:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        for i in range(5100):
            cursor.execute(
                "INSERT INTO usage_analytics (query, normalized, intent, capability, latency_ms) VALUES (?, ?, ?, ?, ?)",
                (f"q{i}", "q", "intent", "calc", 10)
            )
        conn.commit()
        
        # Call pruning via logger
        analytics_service.log_interaction("test", "test", "test", "llm", False, True, 20)
        
        cursor.execute("SELECT COUNT(*) as count FROM usage_analytics")
        count = cursor.fetchone()["count"]
        conn.close()
        
        # Pruning should keep exactly 5000 rows (plus the new log row = 5000)
        self.assertEqual(count, 5000)

    def test_cache_ttl_and_exclusions(self):
        # 1. Weather query caching
        response_cache.set_cached_response("weather in Mumbai", "Sunny 30C")
        cached = response_cache.get_cached_response("weather in Mumbai")
        self.assertEqual(cached, "Sunny 30C")
        
        # Mock weather cache row age to be expired (> 10 mins / 600s)
        conn = db_manager.get_connection()
        now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        old_time = (now_naive_utc - timedelta(minutes=11)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE response_cache SET timestamp = ? WHERE prompt = ?", (old_time, "weather in mumbai"))
        conn.commit()
        conn.close()
        
        # Querying expired weather cache should evict it and return None
        cached_expired = response_cache.get_cached_response("weather in Mumbai")
        self.assertIsNone(cached_expired)
        
        # 2. Verify exclusions (DateTime, Battery, Clipboard are NOT cached)
        response_cache.set_cached_response("time is it", "12:00 PM")
        cached_time = response_cache.get_cached_response("time is it")
        self.assertIsNone(cached_time)
        
        response_cache.set_cached_response("battery status", "85%")
        cached_batt = response_cache.get_cached_response("battery status")
        self.assertIsNone(cached_batt)

    def test_affection_system_boundaries(self):
        # Upgrades affection check
        # Under 30 interactions: Stranger
        state_manager.update_affection()
        self.assertEqual(state_manager.affection_level, "Stranger")
        
        # Simulate active days and interactions in database
        conn = db_manager.get_connection()
        # Add 35 interactions
        for i in range(35):
            conn.execute("INSERT INTO usage_analytics (query, normalized, intent, capability, latency_ms) VALUES ('q', 'q', 'intent', 'conversation', 10)")
        conn.commit()
        conn.close()
        
        # 35 interactions: Acquaintance
        state_manager.update_affection()
        self.assertEqual(state_manager.affection_level, "Acquaintance")

if __name__ == '__main__':
    unittest.main()
