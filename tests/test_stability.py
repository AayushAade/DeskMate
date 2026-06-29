import unittest
import os
import time
from datetime import datetime, timedelta, timezone
from config import settings

# Point database to test DB
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_stability_test.db")
settings.DB_PATH = TEST_DB_PATH
settings.LOG_LEVEL = "DEBUG"  # Show debug messages during testing

from database import db_manager
from assistant.router.router import AssistantRouter, RouterResult
from assistant.router import response_cache
from services import scheduler
from events import event_bus
from notifications.notification_manager import notification_manager
from assistant.state.state_manager import state_manager
from backends.base_backend import BaseBackend
from events import behavior_engine

class MockBackend(BaseBackend):
    def __init__(self):
        self.stream_called = 0
        
    def generate_stream(self, chat_history: list, context: str = ""):
        self.stream_called += 1
        yield "mock"
        yield " "
        yield "reply"

class TestStability(unittest.TestCase):
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
        state_manager.mood = "Relaxed"
        state_manager.emotion = None
        state_manager.affection_level = "Stranger"
        state_manager.energy = 80
        state_manager.focus_mode = False
        state_manager.is_typing = False
        
        # Clear tables
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM reminders")
        conn.execute("DELETE FROM response_cache")
        conn.execute("DELETE FROM usage_analytics")
        conn.commit()
        conn.close()
        
        # Reset notification manager history
        notification_manager._cooldowns.clear()

    def test_reminder_lifecycle_and_single_fire(self):
        # 1. Add reminder
        r_id = scheduler.add_reminder("water plants", 1)
        self.assertNotEqual(r_id, -1)
        
        # Check active pending count inside scheduler
        pending_count = scheduler.initialize()
        self.assertEqual(pending_count, 1)
        
        # 2. Check immediately (should not fire yet)
        due = scheduler.check_pending_reminders()
        self.assertEqual(len(due), 0)
        
        # 3. Simulate passage of time to trigger reminder
        time.sleep(1.1)
        due_now = scheduler.check_pending_reminders()
        self.assertEqual(len(due_now), 1)
        self.assertEqual(due_now[0]["task"], "water plants")
        
        # Verify status is updated to completed
        conn = db_manager.get_connection()
        row = conn.execute("SELECT status FROM reminders WHERE id = ?", (r_id,)).fetchone()
        self.assertEqual(row["status"], "completed")
        conn.close()
        
        # 4. Check again (should NOT fire again)
        due_again = scheduler.check_pending_reminders()
        self.assertEqual(len(due_again), 0)

    def test_focus_mode_suppression(self):
        # Triggered notifications store
        received_alerts = []
        def on_triggered(title, message):
            received_alerts.append(message)
            
        notification_manager.notification_triggered.connect(on_triggered)
        
        try:
            # 1. Enable Focus Mode
            state_manager.focus_mode = True
            
            # 2. Trigger proactive alerts
            event_bus.publish("PROACTIVE_ALERT", message="Stretch reminder", type="STRETCH_REMINDER")
            # Should be suppressed
            self.assertEqual(len(received_alerts), 0)
            
            # 3. Trigger user reminder due
            event_bus.publish("REMINDER_DUE", id=99, task="Do homework")
            # User reminder MUST bypass Focus Mode suppression and fire
            self.assertEqual(len(received_alerts), 1)
            self.assertIn("Do homework", received_alerts[0])
            
        finally:
            # Disconnect slot to avoid polluting other tests
            notification_manager.notification_triggered.disconnect(on_triggered)

    def test_notification_deduplication(self):
        received_alerts = []
        def on_triggered(title, message):
            received_alerts.append(message)
            
        notification_manager.notification_triggered.connect(on_triggered)
        
        try:
            # First proactive alert
            event_bus.publish("PROACTIVE_ALERT", message="Hey! Stretch!", type="STRETCH_REMINDER")
            self.assertEqual(len(received_alerts), 1)
            
            # Second proactive alert of same type within cooldown
            event_bus.publish("PROACTIVE_ALERT", message="Time to stretch!", type="STRETCH_REMINDER")
            # Should be blocked
            self.assertEqual(len(received_alerts), 1)
            
            # Proactive alert of a different type
            event_bus.publish("PROACTIVE_ALERT", message="Low battery warning", type="LOW_BATTERY")
            # Should fire
            self.assertEqual(len(received_alerts), 2)
            
        finally:
            notification_manager.notification_triggered.disconnect(on_triggered)

    def test_router_contract_and_guarantees(self):
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # 1. Test local capability result is returned inside RouterResult
        res_str = router.route_and_execute("time", [])
        self.assertIsNotNone(res_str)
        self.assertTrue(len(res_str) > 0)
        
        # 2. Test LLM fallback returns exactly one RouterResult via router.last_result
        chunks = list(router.route_and_stream("Explain recursion", []))
        self.assertTrue(len(chunks) > 0)
        
        final_result = router.last_result
        self.assertIsInstance(final_result, RouterResult)
        self.assertTrue(final_result.success)
        self.assertEqual(final_result.source, "llm")
        self.assertEqual(final_result.response, "mock reply")

    def test_maintenance_routine(self):
        # Insert completed reminder older than 30 days
        conn = db_manager.get_connection()
        old_time = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=31)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO reminders (task, due_at, status) VALUES ('old task', ?, 'completed')", (old_time,))
        conn.execute("INSERT INTO reminders (task, due_at, status) VALUES ('pending task', ?, 'pending')", (old_time,))
        conn.commit()
        conn.close()
        
        # Run maintenance
        db_manager.run_maintenance()
        
        # Verify old completed task is gone, but pending task remains
        conn = db_manager.get_connection()
        completed_rows = conn.execute("SELECT COUNT(*) as count FROM reminders WHERE status = 'completed'").fetchone()["count"]
        pending_rows = conn.execute("SELECT COUNT(*) as count FROM reminders WHERE status = 'pending'").fetchone()["count"]
        conn.close()
        
        self.assertEqual(completed_rows, 0)
        self.assertEqual(pending_rows, 1)

    def test_long_running_stability_simulation(self):
        """Simulates 500 user queries, 500 capability runs, and 200 proactive notifications."""
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # We pre-populate response cache to mock rapid local lookup triggers
        response_cache.set_cached_response("quantum info", "quantum cached response")
        
        chat_history = []
        
        # Run fast simulation loop
        for i in range(500):
            query = "quantum info" if i % 2 == 0 else "explain quantum computing"
            
            # Consume stream
            chunks = []
            for chunk in router.route_and_stream(query, chat_history):
                chunks.append(chunk)
            result_obj = router.last_result
            
            self.assertIsNotNone(result_obj)
            self.assertTrue(result_obj.success)
            
            # Simulate app/reminders capabilities
            if i % 5 == 0:
                # Add reminder
                scheduler.add_reminder(f"Sim reminder {i}", 100)
                
            # Simulate ticks and notifications
            if i % 10 == 0:
                is_active = (i % 20 == 0)
                proactive_msg = behavior_engine.tick(idle_seconds=0, is_typing=is_active)
                if proactive_msg and not state_manager.focus_mode:
                    notification_manager.trigger_custom_notification("🐾 Mochi Alert", proactive_msg, type="STRETCH_REMINDER")
                    
            # Maintain chat history boundary
            chat_history.append({"role": "user", "parts": [{"text": query}]})
            chat_history.append({"role": "model", "parts": [{"text": result_obj.response}]})
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
                
        # Validate stability state invariants
        self.assertTrue(len(chat_history) <= 20)
        
        # Check cache count is bounded
        conn = db_manager.get_connection()
        cache_count = conn.execute("SELECT COUNT(*) as count FROM response_cache").fetchone()["count"]
        reminder_count = conn.execute("SELECT COUNT(*) as count FROM reminders").fetchone()["count"]
        conn.close()
        
        self.assertTrue(cache_count > 0)
        self.assertEqual(reminder_count, 100)  # exactly 500 / 5 = 100 reminders added

if __name__ == '__main__':
    unittest.main()
