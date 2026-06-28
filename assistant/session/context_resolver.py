# Conversation Context State
_context = {
    "last_capability": None,
    "last_location": None,
    "last_file": None,
    "last_search": None,
    "last_app": None,
    "last_topic": None,
    "last_search_results": []
}

def update_context(capability: str, data: dict):
    """Updates the conversation context states when a capability is executed using its output data."""
    global _context
    _context["last_capability"] = capability
    
    if capability == "weather" and data.get("city"):
        _context["last_location"] = data.get("city")
    elif capability == "files" and data.get("file_path"):
        _context["last_file"] = data.get("file_path")
    elif capability == "search":
        if data.get("query"):
            _context["last_search"] = data.get("query")
        if data.get("results"):
            _context["last_search_results"] = data.get("results")
    elif capability == "apps" and data.get("app_name"):
        _context["last_app"] = data.get("app_name")

def get_context_value(key: str):
    """Retrieves a specific context value by key."""
    return _context.get(key)

def get_all_context() -> dict:
    """Returns the entire active context dictionary."""
    return dict(_context)

def clear_context():
    """Resets the context states."""
    global _context
    for k in _context:
        if k == "last_search_results":
            _context[k] = []
        else:
            _context[k] = None
