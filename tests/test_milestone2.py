import unittest
import os
import shutil
from config import settings

# Point database to test db
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from assistant.router.router import AssistantRouter
from capabilities.base_capability import Intent, CapabilityResult
from backends.base_backend import BaseBackend

class MockBackend(BaseBackend):
    def generate_response(self, chat_history: list, context: str = "") -> str:
        return "mock llm"

class TestMilestone2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_manager.init_db()
        cls.test_files_dir = os.path.join(os.path.dirname(__file__), "test_files")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass
        if os.path.exists(cls.test_files_dir):
            try:
                shutil.rmtree(cls.test_files_dir)
            except Exception:
                pass

    def test_datetime_capability(self):
        router = AssistantRouter()
        # Find datetime capability
        cap = next(c for c in router.capabilities if c.name == "datetime")
        
        intent = cap.match_and_extract("What is today's date?")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.capability, "datetime")
        
        result = cap.execute(intent.parameters)
        self.assertTrue(result.success)
        self.assertIn("date", result.data)
        self.assertIn("time", result.data)
        self.assertIn("Nya!", result.message)

    def test_battery_capability(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "battery")
        
        intent = cap.match_and_extract("battery status please")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.capability, "battery")
        
        result = cap.execute(intent.parameters)
        # Even if battery read fails due to hardware virtualisation in some environments,
        # it should return a structured result with success=True or success=False,
        # not crash!
        self.assertIsInstance(result, CapabilityResult)
        if result.success:
            self.assertIn("percent", result.data)
            self.assertIn("charging", result.data)

    def test_clipboard_capability(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "clipboard")
        
        intent = cap.match_and_extract("what's on my clipboard?")
        self.assertIsNotNone(intent)
        
        result = cap.execute(intent.parameters)
        self.assertIsInstance(result, CapabilityResult)
        if result.success:
            self.assertIn("content", result.data)

    def test_files_capability(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "files")
        
        # Write dummy txt file
        test_file = os.path.join(self.test_files_dir, "note.txt")
        with open(test_file, "w") as f:
            f.write("Mochi loves fish!")
            
        intent = cap.match_and_extract(f"Read file {test_file}")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.parameters["file_path"], test_file)
        
        result = cap.execute(intent.parameters)
        self.assertTrue(result.success)
        self.assertEqual(result.data["content"], "Mochi loves fish!")
        self.assertFalse(result.data["truncated"])
        self.assertIn("Mochi loves fish!", result.message)
        
        # Test Truncation (over 2000 chars)
        large_file = os.path.join(self.test_files_dir, "large.md")
        large_content = "x" * 2500
        with open(large_file, "w") as f:
            f.write(large_content)
            
        intent_l = cap.match_and_extract(f"show contents of {large_file}")
        result_l = cap.execute(intent_l.parameters)
        self.assertTrue(result_l.success)
        self.assertTrue(result_l.data["truncated"])
        self.assertEqual(len(result_l.data["content"]), 2000)

    def test_weather_capability_extract(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "weather")
        
        intent = cap.match_and_extract("what's the weather in Tokyo?")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.parameters.get("city"), "tokyo")
        
        # Test default weather (no city specified)
        intent_default = cap.match_and_extract("Is it raining today?")
        self.assertIsNotNone(intent_default)
        self.assertNotIn("city", intent_default.parameters)

    def test_search_capability_extract(self):
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "search")
        
        intent = cap.match_and_extract("search the web for python concurrency tutorials")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.parameters["query"], "python concurrency tutorials")

    def test_router_selects_correct_capabilities(self):
        router = AssistantRouter()
        router._backend = MockBackend()
        
        # Check routing
        self.assertIn("Nya!", router.route_and_execute("what time is it?", []))
        self.assertIn("Battery is at", router.route_and_execute("how much battery do I have?", []))
        
        # Check calculator
        self.assertIn("184", router.route_and_execute("calculate 92 * 2", []))
        
        # Check LLM fallback (should return mock)
        self.assertEqual(router.route_and_execute("hello mochi, do you like milk?", []), "mock llm")

if __name__ == '__main__':
    unittest.main()
