import unittest
import os
from config import settings

# Redirect to test db
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_test_memory.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from memory import working_memory, semantic_memory, episodic_memory, policy, relevance_scorer
from capabilities.base_capability import Intent, CapabilityResult
from assistant.router.router import AssistantRouter
from backends.base_backend import BaseBackend

class MockBackend(BaseBackend):
    def __init__(self):
        self.received_context = ""
        
    def generate_response(self, chat_history: list, context: str = "") -> str:
        self.received_context = context
        return f"Response with context: {context}"

class TestMilestone3(unittest.TestCase):
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
        # Clear tables
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM chat_history")
        conn.execute("DELETE FROM preferences")
        conn.execute("DELETE FROM episodic_memory")
        conn.commit()
        conn.close()
        working_memory.clear_history()

    def test_working_memory(self):
        # Test addition and transient limits
        for i in range(25):
            working_memory.add_message("user" if i % 2 == 0 else "model", f"message {i}")
            
        history = working_memory.get_history()
        self.assertEqual(len(history), 20) # capped at 20
        self.assertEqual(history[0]["text"], "message 5")
        self.assertEqual(history[-1]["text"], "message 24")

    def test_semantic_memory(self):
        semantic_memory.save_fact("studies", "Artificial Intelligence")
        semantic_memory.save_fact("user_name", "Aayush")
        
        all_facts = semantic_memory.get_all_facts()
        self.assertEqual(len(all_facts), 2)
        self.assertEqual(all_facts["studies"], "Artificial Intelligence")
        self.assertEqual(all_facts["user_name"], "Aayush")
        
        semantic_memory.delete_fact("user_name")
        self.assertIsNone(semantic_memory.get_fact("user_name"))

    def test_memory_policy(self):
        # Test semantic fact matching
        t1, k1, v1 = policy.analyze_input("My name is Aayush")
        self.assertEqual(t1, "semantic")
        self.assertEqual(k1, "user_name")
        self.assertEqual(v1, "Aayush")
        
        t2, k2, v2 = policy.analyze_input("I study Computer Science")
        self.assertEqual(t2, "semantic")
        self.assertEqual(k2, "studies")
        self.assertEqual(v2, "Computer science")
        
        # Test custom key mapping (e.g. likes)
        t3, k3, v3 = policy.analyze_input("I love programming in Python")
        self.assertEqual(t3, "semantic")
        self.assertEqual(k3, "programming_language")
        self.assertEqual(v3, "Python")

        t3_b, k3_b, v3_b = policy.analyze_input("I like cats")
        self.assertEqual(t3_b, "semantic")
        self.assertEqual(k3_b, "likes_cats")
        self.assertEqual(v3_b, "Cats")

        # Test direct accomplishments
        t4, k4, v4 = policy.analyze_input("Today I finished Milestone 2")
        self.assertEqual(t4, "episodic")
        self.assertEqual(v4, "Today I finished Milestone 2")
        
        # Test normal queries (no storage)
        t5, k5, v5 = policy.analyze_input("what is the weather in Delhi?")
        self.assertEqual(t5, "none")

    def test_relevance_scorer_and_episodic_summaries(self):
        # Insert test semantic fact
        semantic_memory.save_fact("user_name", "Aayush")
        semantic_memory.save_fact("programming_language", "Python")
        
        # Insert test episodic memory
        conn = db_manager.get_connection()
        conn.execute("INSERT INTO episodic_memory (summary) VALUES ('User worked on Mochi desktop pet project')")
        conn.execute("INSERT INTO episodic_memory (summary) VALUES ('User discussed SQLite schemas')")
        conn.commit()
        conn.close()
        
        # Query matching fact
        context1 = relevance_scorer.retrieve_relevant_context("What is my name?")
        self.assertIn("Aayush", context1)
        
        # Query matching episodic memory
        context2 = relevance_scorer.retrieve_relevant_context("Tell me about the Mochi pet project")
        self.assertIn("Mochi desktop pet project", context2)
        
        # Heuristic summarizer test
        history = [
            {"role": "user", "text": "What is 2 + 2?"},
            {"role": "model", "text": "4"},
            {"role": "user", "text": "open Chrome"}
        ]
        summary = episodic_memory.generate_heuristic_summary(history)
        self.assertIn("calculations", summary)
        self.assertIn("opening apps", summary)

    def test_memory_capability(self):
        # Setup facts
        semantic_memory.save_fact("user_name", "Aayush")
        semantic_memory.save_fact("device", "MacBook Air M2")
        
        router = AssistantRouter()
        cap = next(c for c in router.capabilities if c.name == "memory")
        
        intent = cap.match_and_extract("what do you remember about me?")
        self.assertIsNotNone(intent)
        
        result = cap.execute(intent.parameters)
        self.assertTrue(result.success)
        self.assertIn("Aayush", result.message)
        self.assertIn("MacBook Air M2", result.message)
        self.assertIn("building me", result.message)

    def test_router_context_injection(self):
        # Save a fact
        semantic_memory.save_fact("user_name", "Aayush")
        
        router = AssistantRouter()
        mock_backend = MockBackend()
        router._backend = mock_backend
        
        # Route a query that falls back to LLM
        response = router.route_and_execute("Tell me a joke about code", [])
        
        # Context should be injected
        self.assertIn("Aayush", mock_backend.received_context)

if __name__ == '__main__':
    unittest.main()
