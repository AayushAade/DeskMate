import unittest
import os
import sqlite3
from config import settings

# Point database to a test database during testing to prevent polluting actual database
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from services import memory_service, app_service
from events import event_bus
from capabilities.base_capability import Intent, CapabilityResult
from assistant.router.router import AssistantRouter
from backends.base_backend import BaseBackend

class MockBackend(BaseBackend):
    def generate_response(self, chat_history: list, context: str = "") -> str:
        return "Meow! This is a mock LLM response! 🐾"

class TestMilestone1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialise the test database
        db_manager.init_db()

    @classmethod
    def tearDownClass(cls):
        # Remove test database
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception as e:
                print(f"Error removing test database file: {e}")

    def setUp(self):
        # Clear tables before each test
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM chat_history")
        conn.execute("DELETE FROM preferences")
        conn.execute("DELETE FROM reminders")
        conn.commit()
        conn.close()

    def test_database_and_memory_service(self):
        # Test Chat History saving and loading
        memory_service.save_chat_message("test_session", "user", "Hello Mochi!")
        memory_service.save_chat_message("test_session", "model", "Mrrp! Hello!")
        
        history = memory_service.get_chat_history("test_session")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["text"], "Hello Mochi!")
        self.assertEqual(history[1]["role"], "model")
        self.assertEqual(history[1]["text"], "Mrrp! Hello!")
        
        # Test Preference storing and retrieving
        memory_service.set_preference("user_name", "Aayush")
        self.assertEqual(memory_service.get_preference("user_name"), "Aayush")
        
        # Test overwriting preference
        memory_service.set_preference("user_name", "Bob")
        self.assertEqual(memory_service.get_preference("user_name"), "Bob")
        
        # Test default value retrieval
        self.assertEqual(memory_service.get_preference("missing_key", "default_val"), "default_val")

    def test_event_bus(self):
        events_received = []
        
        def on_test_event(data):
            events_received.append(data)
            
        event_bus.subscribe("TEST_EVENT", on_test_event)
        event_bus.publish("TEST_EVENT", data="purr")
        
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0], "purr")
        
        # Unsubscribe
        event_bus.unsubscribe("TEST_EVENT", on_test_event)
        event_bus.publish("TEST_EVENT", data="meow")
        self.assertEqual(len(events_received), 1) # unchanged

    def test_calculator_capability(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "calculator")
        
        # Test matching regex
        intent = cap.match_and_extract("what is 47 * 2")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.capability, "calculator")
        self.assertEqual(intent.parameters["expression"], "47 * 2")
        
        # Test execution
        result = cap.execute(intent.parameters)
        self.assertTrue(result.success)
        self.assertEqual(result.data["result"], 94)
        self.assertIn("94", result.message)
        
        # Test scientific function
        intent_sci = cap.match_and_extract("evaluate sqrt(144)")
        self.assertIsNotNone(intent_sci)
        result_sci = cap.execute(intent_sci.parameters)
        self.assertTrue(result_sci.success)
        self.assertEqual(result_sci.data["result"], 12.0)

    def test_apps_capability(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "apps")
        
        # Test matching
        intent = cap.match_and_extract("open VS Code")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.parameters["app_name"], "vs code")
        
        # We don't want to actually launch apps during tests (or if we do, it is fine since it runs open -a).
        # To avoid side-effects in testing, we mock app_service.launch_app:
        original_launch = app_service.launch_app
        try:
            app_service.launch_app = lambda name: (True, "Visual Studio Code", "mock success")
            result = cap.execute(intent.parameters)
            self.assertTrue(result.success)
            self.assertEqual(result.data["app_name"], "Visual Studio Code")
            self.assertIn("Visual Studio Code", result.message)
        finally:
            app_service.launch_app = original_launch

    def test_router_routing_and_fallback(self):
        router = AssistantRouter()
        
        # Mock active backend to avoid calling actual local Ollama server
        router._backend = MockBackend()
        
        # Test direct routing to Calculator
        msg = router.route_and_execute("calculate 10 + 5", [])
        self.assertIn("15", msg)
        
        # Test fallback to LLM
        fallback_msg = router.route_and_execute("write a poem about milk", [])
        self.assertEqual(fallback_msg, "Meow! This is a mock LLM response! 🐾")

if __name__ == '__main__':
    unittest.main()
