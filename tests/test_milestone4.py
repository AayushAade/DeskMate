import unittest
import os
import time
from config import settings

# Point database to a test database during testing to prevent polluting actual database
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from assistant.router.router import AssistantRouter
from assistant.router import response_cache
from assistant.session import context_resolver
from services import scheduler
from events import event_bus
from events import behavior_engine
from capabilities.reminders.reminders_capability import RemindersCapability
from backends.base_backend import BaseBackend

class MockBackend(BaseBackend):
    def __init__(self):
        self.stream_called = False
        
    def generate_stream(self, chat_history: list, context: str = ""):
        self.stream_called = True
        yield "mock"
        yield " "
        yield "streamed"
        yield " "
        yield "text"

class TestMilestone4(unittest.TestCase):
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
        context_resolver.clear_context()
        from assistant.state.state_manager import state_manager
        state_manager.mood = "Happy"
        # Clear cache and reminders tables
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM response_cache")
        conn.execute("DELETE FROM reminders")
        conn.commit()
        conn.close()

    def test_response_caching(self):
        # 1. Verify cache write and read
        response_cache.set_cached_response("explain quantum physics", "Quantum physics is cool!")
        cached = response_cache.get_cached_response("explain quantum physics")
        self.assertEqual(cached, "Quantum physics is cool!")
        
        # 2. Case and spacing insensitivity
        cached_case = response_cache.get_cached_response("Explain Quantum Physics?")
        self.assertEqual(cached_case, "Quantum physics is cool!")
        
        # 3. Router avoids LLM call on cache hit
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        msg = router.route_and_execute("explain quantum physics", [])
        self.assertEqual(msg, "Quantum physics is cool!")
        self.assertFalse(mock_backend.stream_called)

    def test_response_streaming(self):
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # Router route_and_stream yields tokens
        tokens = list(router.route_and_stream("some random LLM prompt", []))
        self.assertTrue(mock_backend.stream_called)
        self.assertEqual(tokens, ["mock", " ", "streamed", " ", "text"])

    def test_behavior_engine_and_mood_shifts(self):
        from assistant.state.state_manager import state_manager
        # Initial mood
        self.assertEqual(state_manager.mood, "Happy")
        
        # Test event updates mood / emotion
        event_bus.publish("APP_LAUNCHED", app_name="vs code", success=True)
        self.assertEqual(state_manager.emotion, "Excited")
        
        event_bus.publish("CALCULATION_COMPLETED", expression="2+2", result=4)
        self.assertEqual(state_manager.mood, "Focused")
        
        # Test typing ticks for coding duration stretch reminder
        proactive_msg = None
        for i in range(20):
            msg = behavior_engine.tick(idle_seconds=0, is_typing=True)
            if msg:
                proactive_msg = msg
                
        self.assertEqual(state_manager.mood, "Sleepy")
        self.assertIsNotNone(proactive_msg)
        self.assertIn("stretch", proactive_msg)

    def test_scheduler_and_reminders_capability(self):
        # 1. Parse capability input
        cap = RemindersCapability()
        intent = cap.match_and_extract("remind me to walk the dog in 5 minutes")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.parameters["task"], "walk the dog")
        self.assertEqual(intent.parameters["delay_seconds"], 300)
        
        # 2. Add reminder to database
        rem_id = scheduler.add_reminder("drink water", 1)
        self.assertNotEqual(rem_id, -1)
        
        # Check not due yet
        due = scheduler.check_pending_reminders()
        self.assertEqual(len(due), 0)
        
        # Sleep to let it expire
        time.sleep(1.1)
        due_now = scheduler.check_pending_reminders()
        self.assertEqual(len(due_now), 1)
        self.assertEqual(due_now[0]["task"], "drink water")

if __name__ == '__main__':
    unittest.main()
