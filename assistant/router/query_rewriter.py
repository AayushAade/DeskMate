import re
from assistant.session import context_resolver

def rewrite_query(query: str) -> str:
    """
    Rewrites an incomplete query into an explicit one using context in <1ms.
    """
    q = query.strip()
    
    # Get previous capability and context values
    last_cap = context_resolver.get_context_value("last_capability")
    last_loc = context_resolver.get_context_value("last_location")
    last_app = context_resolver.get_context_value("last_app")
    last_search = context_resolver.get_context_value("last_search")
    last_search_results = context_resolver.get_context_value("last_search_results")
    
    # 1. Weather Capability follow-ups
    if last_cap == "weather":
        # Check if query is just a city name or a follow-up about location
        # E.g. "in Pune", "how about Pune?", "and Navi Mumbai?"
        city_match = re.search(r'\b(?:how about|what about|and|in)\s+([a-za-z\s\-]+)', q, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()
            # If it's a relative time like "tomorrow", don't treat it as a city
            if city not in ["tomorrow", "today", "next week"]:
                return f"weather in {city}"
                
        # E.g. "what about tomorrow?", "tomorrow?"
        if "tomorrow" in q.lower():
            loc = last_loc if last_loc else ""
            return f"weather forecast in {loc}".strip()

    # 2. Search Capability follow-ups
    elif last_cap == "search":
        # E.g. "open the first result" or "open 2nd link"
        result_match = re.search(r'\bopen\s+(?:the\s+)?(first|second|third|1st|2nd|3rd|1|2|3)\s+(?:result|link|source)\b', q, re.IGNORECASE)
        if result_match and last_search_results:
            rank = result_match.group(1).lower()
            idx = 0
            if rank in ["second", "2nd", "2"]:
                idx = 1
            elif rank in ["third", "3rd", "3"]:
                idx = 2
                
            if idx < len(last_search_results):
                url = last_search_results[idx]["href"]
                return f"open {url}"
                
        search_match = re.search(r'\b(?:how about|what about|and)\s+([a-za-z0-9\s\-]+)', q, re.IGNORECASE)
        if search_match:
            new_search = search_match.group(1).strip()
            return f"search {new_search}"

    # 3. Apps Capability follow-ups
    elif last_cap == "apps":
        # E.g. "close it" -> close the last app
        if q.lower() == "close it" and last_app:
            return f"close {last_app}"
        # E.g. "open terminal too" -> "open terminal"
        open_too = re.search(r'\bopen\s+([a-za-z0-9\s\-]+)\s+too\b', q, re.IGNORECASE)
        if open_too:
            return f"open {open_too.group(1).strip()}"

    # 4. Standard replacements (e.g. open vs launch)
    if q.lower().startswith("open ") or q.lower().startswith("launch ") or q.lower().startswith("run "):
        return q

    return q
