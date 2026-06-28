import time
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
from capabilities.reminders.reminders_capability import RemindersCapability

from backends.ollama_backend import OllamaBackend
from config import settings

from assistant.router import query_normalizer, intent_detector, query_rewriter, response_cache
from assistant.session import context_resolver
from memory import relevance_scorer
from services import analytics_service
from events import event_bus
from assistant.state.state_manager import state_manager

class AssistantRouter:
    def __init__(self):
        # Register capabilities in priority order
        self.capabilities = [
            ConversationCapability(),  # High priority: intercepts greetings/farewells locally
            RemindersCapability(),
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
        Sync execution: consumes the stream and returns a single concatenated string.
        Useful for unit tests and simple sync integrations.
        """
        chunks = []
        for chunk in self.route_and_stream(query, chat_history):
            chunks.append(chunk)
        return "".join(chunks)

    def route_and_stream(self, query: str, chat_history: list):
        """
        Streams query execution: yields text tokens.
        Measures routing overhead, cache hits, execution latencies, and logs timeline steps.
        """
        timeline = []
        start_time = time.time()
        
        # 1. Normalize query
        timeline.append((time.time(), "Query normalization initiated"))
        normalized = query_normalizer.normalize_query(query)
        timeline.append((time.time(), f"Query normalized: '{normalized}'"))
        
        # 2. Detect conversational intent
        timeline.append((time.time(), "Intent detection initiated"))
        detected_intent = intent_detector.detect_intent(normalized)
        intent_type = detected_intent.capability
        timeline.append((time.time(), f"Detected conversational intent: '{intent_type}'"))
        
        # 3. Resolve context and rewrite query if needed (e.g. follow-ups)
        timeline.append((time.time(), "Context resolution & query rewrite check"))
        rewritten = query_rewriter.rewrite_query(normalized)
        if rewritten != normalized:
            timeline.append((time.time(), f"Query rewritten: '{rewritten}'"))
        else:
            timeline.append((time.time(), "Query remains unchanged"))
        
        # 4. Match capability
        timeline.append((time.time(), "Capability matching started"))
        matched_cap = None
        matched_intent = None
        
        for cap in self.capabilities:
            intent = cap.match_and_extract(rewritten)
            if intent is not None:
                matched_cap = cap
                matched_intent = intent
                break
                
        # 5. Execute matching local capability (Instant single-chunk stream)
        if matched_cap is not None:
            router_overhead = (time.time() - start_time) * 1000
            timeline.append((time.time(), f"Matched local capability: '{matched_cap.name}' (Overhead: {router_overhead:.2f}ms)"))
            
            exec_start = time.time()
            result = matched_cap.execute(matched_intent.parameters)
            exec_latency = (time.time() - exec_start) * 1000
            total_latency = (time.time() - start_time) * 1000
            
            timeline.append((time.time(), f"Executed '{matched_cap.name}' in {exec_latency:.2f}ms (Total: {total_latency:.2f}ms)"))
            
            # Update session context with execution output data
            context_resolver.update_context(matched_cap.name, result.data)
            
            # Update StateManager
            state_manager.handle_event("USER_MESSAGE")
            # Set state manager capabilities
            state_manager.current_capability = matched_cap.name
            state_manager.last_capability = matched_cap.name
            
            # Map capability name to event name for transitions
            cap_event = f"{matched_cap.name.upper()}_COMPLETED"
            # Special naming conversions if needed
            if matched_cap.name == "weather":
                cap_event = "WEATHER_FETCHED"
            state_manager.handle_event(cap_event, result.data)
            
            # Write analytics log
            analytics_service.log_interaction(
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability=matched_cap.name,
                cache_hit=False,
                llm_called=False,
                latency_ms=int(total_latency)
            )
            
            # Publish complete telemetry event
            event_bus.publish(
                "ROUTING_COMPLETED",
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability=matched_cap.name,
                cache_hit=False,
                llm_called=False,
                router_overhead=router_overhead,
                execution_latency=exec_latency,
                total_latency=total_latency,
                timeline=timeline
            )
            
            yield result.message
            return
            
        # 6. Check response cache to avoid LLM inference
        timeline.append((time.time(), "Checking response cache..."))
        cached = response_cache.get_cached_response(rewritten)
        if cached:
            router_overhead = (time.time() - start_time) * 1000
            total_latency = router_overhead
            timeline.append((time.time(), f"Cache hit! Evading LLM call (Total: {total_latency:.2f}ms)"))
            
            # Update StateManager
            state_manager.handle_event("USER_MESSAGE")
            state_manager.current_capability = "llm"
            context_resolver.update_context("llm", {})
            
            analytics_service.log_interaction(
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability="llm (cached)",
                cache_hit=True,
                llm_called=False,
                latency_ms=int(total_latency)
            )
            
            event_bus.publish(
                "ROUTING_COMPLETED",
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability="llm (cached)",
                cache_hit=True,
                llm_called=False,
                router_overhead=router_overhead,
                execution_latency=0.0,
                total_latency=total_latency,
                timeline=timeline
            )
            
            yield cached
            return

        # 7. Fall back to LLM backend (Last Resort)
        router_overhead = (time.time() - start_time) * 1000
        timeline.append((time.time(), f"Cache miss. Routing to LLM stream fallback (Overhead: {router_overhead:.2f}ms)"))
        
        # Retrieve relevant memories for LLM prompt enhancement
        timeline.append((time.time(), "Querying memory relevance scorer..."))
        context = relevance_scorer.retrieve_relevant_context(rewritten)
        memory_count = len(context.split("\n")) if context else 0
        timeline.append((time.time(), f"Injected {memory_count} memory facts into system prompt"))
        
        # Update StateManager
        state_manager.handle_event("USER_MESSAGE")
        state_manager.current_capability = "llm"
        context_resolver.update_context("llm", {})
        
        backend = self.get_backend()
        
        # Stream response from backend, accumulate tokens, and yield
        tokens = []
        exec_start = time.time()
        timeline.append((time.time(), "Inference started on LLM model"))
        
        try:
            for token in backend.generate_stream(chat_history, context=context):
                tokens.append(token)
                yield token
                
            exec_latency = (time.time() - exec_start) * 1000
            total_latency = (time.time() - start_time) * 1000
            timeline.append((time.time(), f"LLM stream finished in {exec_latency:.2f}ms (Total: {total_latency:.2f}ms)"))
            
            # Save the full response in the cache
            full_response = "".join(tokens)
            if full_response.strip():
                response_cache.set_cached_response(rewritten, full_response)
                
            analytics_service.log_interaction(
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability="llm",
                cache_hit=False,
                llm_called=True,
                latency_ms=int(total_latency)
            )
            
            event_bus.publish(
                "ROUTING_COMPLETED",
                query=query,
                normalized=normalized,
                intent=intent_type,
                capability="llm",
                cache_hit=False,
                llm_called=True,
                router_overhead=router_overhead,
                execution_latency=exec_latency,
                total_latency=total_latency,
                timeline=timeline
            )
        except Exception as e:
            # Re-raise so worker catches and reports error
            raise e
