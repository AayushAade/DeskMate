import re

# Regex patterns for matching durable semantic facts
FACT_PATTERNS = [
    (r"\bmy name is ([a-za-z\s]+)", "user_name"),
    (r"\bi study ([a-za-z\s\&]+)", "studies"),
    (r"\bi am studying ([a-za-z\s\&]+)", "studies"),
    (r"\bi use a ([a-za-z0-9\s]+)", "device"),
    (r"\bmy laptop is a ([a-za-z0-9\s]+)", "device"),
    (r"\bi like coding in ([a-za-z]+)", "programming_language"),
    (r"\bi like programming in ([a-za-z]+)", "programming_language"),
    (r"\bi love programming in ([a-za-z]+)", "programming_language"),
    (r"\bi like ([a-za-z0-9\s]+)", "likes_{match}"),
    (r"\bi love ([a-za-z0-9\s]+)", "likes_{match}")
]

def analyze_input(query: str) -> tuple:
    """
    Analyzes input query and returns a tuple (memory_type, key, value).
    memory_type can be 'semantic', 'reminder', 'episodic', or 'none'.
    """
    q = query.lower().strip()
    
    # 1. Check for Reminder intent
    if q.startswith("remind me") or "remind me in" in q:
        return "reminder", None, query
        
    # 2. Check for Semantic facts
    for pattern, key_template in FACT_PATTERNS:
        match = re.search(pattern, q)
        if match:
            match_val = match.group(1).strip()
            # Clean up match
            match_val = match_val.replace("?", "").strip()
            
            # Format key if it contains {match}
            if "{match}" in key_template:
                sanitized_match = re.sub(r'[^a-z0-9_]', '_', match_val.lower())
                key = key_template.format(match=sanitized_match)
            else:
                key = key_template
                
            return "semantic", key, match_val.capitalize()
            
    # 3. Check for high-level accomplishments for Episodic Memory
    # E.g. "Today I did X", "Just finished Y"
    if q.startswith("today i") or q.startswith("just finished") or q.startswith("i finished"):
        return "episodic", None, query
        
    # Default: do not store transient questions or general math queries
    return "none", None, None
