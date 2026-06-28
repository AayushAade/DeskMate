import re
from capabilities.base_capability import Intent

# Fast intent pattern matching definitions
GREETING_WORDS = {"hello", "hi", "hey", "yo", "wassup", "good morning", "good night", "greetings"}
FAREWELL_WORDS = {"bye", "goodbye", "exit", "quit", "see you", "bye bye", "tata"}
THANKS_WORDS = {"thanks", "thank", "thx", "appreciate"}
AGREEMENT_WORDS = {"yes", "no", "okay", "ok", "sure", "agreed", "fine", "nope", "yep"}
EXCITEMENT_WORDS = {"wow", "great", "nice", "awesome", "cool", "superb", "yay", "fantastic"}
LAUGHTER_WORDS = {"haha", "lol", "lmao", "hehe", "rofl"}
APOLOGY_WORDS = {"sorry", "apologies", "my bad", "forgive me"}
COMPLIMENT_WORDS = {"cute", "smart", "good cat", "good pet", "lovely", "beautiful", "best cat"}
CONFUSION_WORDS = {"huh", "what", "puzzled", "confused", "i don't get it", "i don't understand"}

def detect_intent(normalized_query: str) -> Intent:
    """
    Classifies the user input query in <1ms to determine intent type.
    Returns an Intent object.
    """
    q = normalized_query.lower().strip()
    words = set(q.split(" "))
    
    # 1. Greetings (Strict: only match if query is only greeting + name)
    has_greeting = q in GREETING_WORDS or words.intersection(GREETING_WORDS)
    if has_greeting:
        clean_q = re.sub(r'\bmochi\b', '', q).strip()
        clean_words = set(clean_q.split(" ")) - GREETING_WORDS - {""}
        if len(clean_words) == 0:
            return Intent(capability="greeting", confidence=0.99, parameters={})
        
    # 2. Farewell (Strict)
    has_farewell = q in FAREWELL_WORDS or words.intersection(FAREWELL_WORDS)
    if has_farewell:
        clean_q = re.sub(r'\bmochi\b', '', q).strip()
        clean_words = set(clean_q.split(" ")) - FAREWELL_WORDS - {""}
        if len(clean_words) == 0:
            return Intent(capability="farewell", confidence=0.99, parameters={})
        
    # 3. Thanks (Strict)
    has_thanks = q in THANKS_WORDS or words.intersection(THANKS_WORDS)
    if has_thanks:
        clean_q = re.sub(r'\bmochi\b', '', q).strip()
        clean_words = set(clean_q.split(" ")) - THANKS_WORDS - {"you", ""}
        if len(clean_words) == 0:
            return Intent(capability="thanks", confidence=0.99, parameters={})
        
    # 4. Agreement
    if q in AGREEMENT_WORDS or words.intersection(AGREEMENT_WORDS):
        return Intent(capability="agreement", confidence=0.95, parameters={"value": q})
        
    # 5. Excitement
    if q in EXCITEMENT_WORDS or words.intersection(EXCITEMENT_WORDS):
        return Intent(capability="excitement", confidence=0.95, parameters={})
        
    # 6. Laughter
    if q in LAUGHTER_WORDS or words.intersection(LAUGHTER_WORDS):
        return Intent(capability="laughter", confidence=0.95, parameters={})
        
    # 7. Apology
    if q in APOLOGY_WORDS or words.intersection(APOLOGY_WORDS):
        return Intent(capability="apology", confidence=0.95, parameters={})
        
    # 8. Compliment
    if any(word in q for word in COMPLIMENT_WORDS):
        return Intent(capability="compliment", confidence=0.90, parameters={})
        
    # 9. Confusion
    if q == "what" or q in CONFUSION_WORDS or words.intersection(CONFUSION_WORDS - {"what"}):
        return Intent(capability="confusion", confidence=0.90, parameters={})
        
    # 10. Weather Follow-up checking (e.g. "what about Navi Mumbai?", "in Pune?")
    # Check if starts with follow-up phrases
    if q.startswith("how about") or q.startswith("what about") or q.startswith("and ") or q.startswith("in "):
        # Check if it has location
        match = re.search(r'\b(?:how about|what about|and|in)\s+([a-za-z\s]+)', q)
        if match:
            entity = match.group(1).strip()
            # If it's a follow-up, mark it and let context resolver determine specific capability
            return Intent(capability="followup", confidence=0.95, parameters={"raw_query": q, "entity": entity})

    # 11. General actions
    if "close it" in q or "close" in q:
        return Intent(capability="app_followup", confidence=0.95, parameters={"action": "close"})

    # 12. Fallback AI categories: Coding, Creative, Reasoning, or General Question
    if any(word in q for word in ["code", "function", "program", "class", "syntax", "debug", "compile", "python", "javascript"]):
        return Intent(capability="coding", confidence=0.85, parameters={"query": query_text(normalized_query)})
        
    if any(word in q for word in ["write a", "poem", "story", "write a song", "make up a", "creative"]):
        return Intent(capability="creative", confidence=0.85, parameters={"query": query_text(normalized_query)})
        
    if any(word in q for word in ["why", "how do i", "explain", "reason", "proof"]):
        return Intent(capability="reasoning", confidence=0.85, parameters={"query": query_text(normalized_query)})
        
    # 13. Default fallback
    return Intent(capability="general_question", confidence=0.50, parameters={"query": query_text(normalized_query)})

def query_text(normalized: str) -> str:
    return normalized
