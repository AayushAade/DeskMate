from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class SearchCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "search"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = ["search", "google", "web search", "duckduckgo", "latest news", "news about", "find info on", "find information on"]
        
        if any(word in q for word in keywords):
            # Clean trigger phrases out of query to form the search search_query
            search_query = query.lower()
            strip_phrases = [
                "search the web for", "web search for", "search for", 
                "google search", "duckduckgo search", "search", 
                "find info on", "find information on"
            ]
            for phrase in strip_phrases:
                search_query = search_query.replace(phrase, "")
            search_query = search_query.replace("?", "").strip()
            
            if not search_query:
                search_query = query.strip()
                
            return Intent(
                capability=self.name,
                confidence=0.94,
                parameters={"query": search_query}
            )
        return None

    def execute(self, params: dict) -> CapabilityResult:
        search_query = params.get("query", "").strip()
        if not search_query:
            return CapabilityResult(
                success=False,
                data={"error": "Empty search query"},
                message="Meow... I couldn't search because the search query was blank! 🐾"
            )
            
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(search_query, max_results=3))
                
            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", "No Title"),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
                
            message = mochi_voice.format_search(search_query, results)
            
            # Fire event
            event_bus.publish("SEARCH_COMPLETED", query=search_query, results_count=len(results))
            
            return CapabilityResult(
                success=True,
                data={"query": search_query, "results": results},
                message=message
            )
            
        except Exception as e:
            event_bus.publish("SEARCH_FAILED", query=search_query, error=str(e))
            return CapabilityResult(
                success=False,
                data={"error": str(e)},
                message=f"Meow... I couldn't search the web! (Error: {e}) 🐾"
            )
