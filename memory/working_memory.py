# In-memory store for the active chat session (transient working memory)
_history = []
MAX_SIZE = 20

def add_message(role: str, text: str):
    """Adds a message to the active conversation history and enforces max size limit."""
    global _history
    _history.append({"role": role, "text": text})
    if len(_history) > MAX_SIZE:
        _history = _history[-MAX_SIZE:]

def get_history() -> list:
    """Returns a list of all active messages in this session."""
    return list(_history)

def clear_history():
    """Clears the transient active conversation store."""
    global _history
    _history.clear()
