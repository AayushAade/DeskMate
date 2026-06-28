from capabilities.datetime.datetime_capability import DateTimeCapability
from capabilities.battery.battery_capability import BatteryCapability
from capabilities.clipboard.clipboard_capability import ClipboardCapability
from capabilities.files.files_capability import FilesCapability
from capabilities.weather.weather_capability import WeatherCapability
from capabilities.search.search_capability import SearchCapability
from capabilities.calculator.calculator_capability import CalculatorCapability
from capabilities.apps.apps_capability import AppsCapability
from capabilities.memory.memory_capability import MemoryCapability
from capabilities.conversation.conversation_capability import ConversationCapability

from backends.ollama_backend import OllamaBackend
from config import settings

from assistant.router import query_normalizer, intent_detector, query_rewriter
from assistant.session import context_resolver
from memory import relevance_scorer

class AssistantRouter:
    def __init__(self):
        # Register capabilities in priority order
        self.capabilities = [
            ConversationCapability(),  # High priority: intercepts greeting/thanks/farewells locally
            DateTimeCapability(),
            BatteryCapability(),
            ClipboardCapability(),
            FilesCapability(),
            WeatherCapability(),
            SearchCapability(),
            MemoryCapability(),
            CalculatorCapability(),
            AppsCapability()
        ]
        self._backend = None

    def get_backend(self):
        """Lazy-loads the LLM backend adapter to avoid blocking at startup."""
        if self._backend is None:
            if settings.ACTIVE_BACKEND == "ollama":
                self._backend = OllamaBackend()
            else:
                raise ValueError(f"Unknown backend type: {settings.ACTIVE_BACKEND}")
        return self._backend

    def route_and_execute(self, query: str, chat_history: list) -> str:
        """
        Routes the user query through the intelligence layer pipeline:
        1. Normalizes query.
        2. Rewrites query based on session context (supports pronouns/follow-ups).
        3. Iterates over registered capabilities for a match.
        4. Executes matching capability, updating session context with output data.
        5. Falls back to LLM backend if no local capability matched.
        """
        # 1. Normalize query
        normalized = query_normalizer.normalize_query(query)
        
        # 2. Resolve context and rewrite query if needed (e.g. follow-ups)
        rewritten = query_rewriter.rewrite_query(normalized)
        
        # 3. Match capability
        matched_cap = None
        matched_intent = None
        
        for cap in self.capabilities:
            intent = cap.match_and_extract(rewritten)
            if intent is not None:
                matched_cap = cap
                matched_intent = intent
                break
                
        # 4. Execute matching local capability
        if matched_cap is not None:
            print(f"[AssistantRouter] Matched capability '{matched_cap.name}' with confidence {matched_intent.confidence}")
            result = matched_cap.execute(matched_intent.parameters)
            
            # Update session context with execution output data
            context_resolver.update_context(matched_cap.name, result.data)
            return result.message
            
        # 5. Fall back to LLM backend (Last Resort)
        print("[AssistantRouter] No capability matched. Routing to LLM backend...")
        
        # Reset capability context since we fell back to general conversation
        context_resolver.update_context("llm", {})
        
        # Retrieve relevant memories for LLM prompt enhancement
        context = relevance_scorer.retrieve_relevant_context(rewritten)
        
        backend = self.get_backend()
        return backend.generate_response(chat_history, context=context)
