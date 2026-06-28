from capabilities.datetime.datetime_capability import DateTimeCapability
from capabilities.battery.battery_capability import BatteryCapability
from capabilities.clipboard.clipboard_capability import ClipboardCapability
from capabilities.files.files_capability import FilesCapability
from capabilities.weather.weather_capability import WeatherCapability
from capabilities.search.search_capability import SearchCapability
from capabilities.calculator.calculator_capability import CalculatorCapability
from capabilities.apps.apps_capability import AppsCapability
from backends.ollama_backend import OllamaBackend
from config import settings

class AssistantRouter:
    def __init__(self):
        # Register capabilities in priority order
        self.capabilities = [
            DateTimeCapability(),
            BatteryCapability(),
            ClipboardCapability(),
            FilesCapability(),
            WeatherCapability(),
            SearchCapability(),
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
        Routes the user query: checks local capabilities first, otherwise falls back to LLM.
        chat_history format: [{"role": "user"|"model", "text": text}]
        """
        cleaned_query = query.strip()
        
        # 1. Check local capabilities (Tier 1 Rule routing)
        for cap in self.capabilities:
            intent = cap.match_and_extract(cleaned_query)
            if intent is not None:
                print(f"[AssistantRouter] Matched capability '{cap.name}' with confidence {intent.confidence}")
                result = cap.execute(intent.parameters)
                return result.message
                
        # 2. Fall back to LLM backend (Tier 2 AI routing)
        print("[AssistantRouter] No capability matched. Routing to LLM backend...")
        backend = self.get_backend()
        
        # We need to construct the prompt and call generate_response
        # Ensure the latest query is appended to history for the LLM call if not already there
        # The chat_history list passed down is managed by the AIWorker
        return backend.generate_response(chat_history)
