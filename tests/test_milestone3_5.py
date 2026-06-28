import unittest
import os
from config import settings

# Redirect db
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from assistant.router.router import AssistantRouter
from assistant.router import query_normalizer, intent_detector, query_rewriter
from assistant.session import context_resolver
from capabilities.base_capability import Intent, CapabilityResult
from backends.base_backend import BaseBackend
from services import app_service

class MockBackend(BaseBackend):
    def __init__(self):
        self.called = False
        
    def generate_response(self, chat_history: list, context: str = "") -> str:
        self.called = True
        return "mock llm"

class TestMilestone3_5(unittest.TestCase):
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

    def test_query_normalization(self):
        # Case conversion & punctuation
        self.assertEqual(query_normalizer.normalize_query("Weather in NaviMumbai!"), "weather in Navi Mumbai")
        self.assertEqual(query_normalizer.normalize_query("temp Pune?"), "weather in Pune")
        self.assertEqual(query_normalizer.normalize_query("forecast"), "weather forecast")
        self.assertEqual(query_normalizer.normalize_query("gm"), "good morning")
        self.assertEqual(query_normalizer.normalize_query("thx"), "thanks")
        
        # City aliases
        self.assertEqual(query_normalizer.normalize_query("weather in mum"), "weather in Mumbai")
        self.assertEqual(query_normalizer.normalize_query("weather in bangalore"), "weather in Bengaluru")

    def test_intent_detection(self):
        # Basic intents
        self.assertEqual(intent_detector.detect_intent("hello").capability, "greeting")
        self.assertEqual(intent_detector.detect_intent("bye").capability, "farewell")
        self.assertEqual(intent_detector.detect_intent("thank you").capability, "thanks")
        
        # Follow ups
        f_intent = intent_detector.detect_intent("how about Navi Mumbai?")
        self.assertEqual(f_intent.capability, "followup")
        self.assertEqual(f_intent.parameters["entity"], "navi mumbai")

    def test_conversation_capability_no_llm(self):
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # Greetings should be handled locally
        msg = router.route_and_execute("Hello Mochi!", [])
        self.assertFalse(mock_backend.called)
        self.assertNotIn("mock llm", msg)
        
        # Farewells should be handled locally
        msg_bye = router.route_and_execute("bye bye", [])
        self.assertFalse(mock_backend.called)
        self.assertNotIn("mock llm", msg_bye)
        
        # Thanks should be handled locally
        msg_thanks = router.route_and_execute("thank you!", [])
        self.assertFalse(mock_backend.called)
        self.assertNotIn("mock llm", msg_thanks)

    def test_weather_followup_location(self):
        router = AssistantRouter()
        
        # 1. Ask about Mumbai weather first
        context_resolver.update_context("weather", {"city": "Mumbai"})
        
        # 2. Ask "how about Pune?"
        rewritten = query_rewriter.rewrite_query("how about Pune?")
        self.assertEqual(rewritten, "weather in Pune")
        
        # 3. Ask "what about tomorrow?" -> should use Mumbai
        rewritten_tomorrow = query_rewriter.rewrite_query("what about tomorrow?")
        self.assertEqual(rewritten_tomorrow, "weather forecast in Mumbai")

    def test_search_and_open_first_result_chain(self):
        router = AssistantRouter()
        
        # Mock search results in context
        mock_results = [
            {"title": "Llama 4 Paper", "href": "https://arxiv.org/llama4", "body": "Summary of Llama 4"},
            {"title": "LLM Agents", "href": "https://arxiv.org/llmagents", "body": "Summary of agents"}
        ]
        context_resolver.update_context("search", {"query": "Llama 4", "results": mock_results})
        
        # Query follow-up: "open the first result"
        rewritten = query_rewriter.rewrite_query("open the first result")
        self.assertEqual(rewritten, "open https://arxiv.org/llama4")
        
        # Execute routing and verify AppsCapability handles URL launching
        original_launch = app_service.launch_app
        url_launched = ""
        def mock_launch(name):
            nonlocal url_launched
            url_launched = name
            return True, name, "launched URL"
            
        app_service.launch_app = mock_launch
        try:
            router.route_and_execute("open the first result", [])
            self.assertEqual(url_launched, "https://arxiv.org/llama4")
        finally:
            app_service.launch_app = original_launch

    def test_llm_fallback(self):
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # General query should trigger LLM fallback
        msg = router.route_and_execute("explain transformer self-attention mechanisms", [])
        self.assertTrue(mock_backend.called)
        self.assertEqual(msg, "mock llm")

if __name__ == '__main__':
    unittest.main()
