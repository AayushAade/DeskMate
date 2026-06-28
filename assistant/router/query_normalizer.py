import re

# Phrase level mappings (before word token splitting)
PHRASE_MAPPINGS = [
    (r"^temp\s+([a-z\s\-]+)$", r"weather in \1"),
    (r"^forecast$", "weather forecast"),
    (r"^thx$", "thanks"),
    (r"^gm$", "good morning"),
]

# Word level mappings
WORD_ALIASES = {
    "navimumbai": "Navi Mumbai",
    "newyork": "New York",
    "banglore": "Bengaluru",
    "bangalore": "Bengaluru",
    "mum": "Mumbai",
    "pune": "Pune",
}

def normalize_query(query: str) -> str:
    """
    Normalizes query in <1ms: lowercases, cleans whitespace/punctuation, 
    expands abbreviations and corrects aliases.
    """
    # 1. Basic cleaning
    q = query.lower().strip()
    q = re.sub(r'\s+', ' ', q)  # Normalize whitespace
    q = q.replace("?", "").replace("!", "").strip()  # Clean punctuation
    
    # 2. Phrase replacements using regex
    for pattern, replacement in PHRASE_MAPPINGS:
        if re.match(pattern, q):
            q = re.sub(pattern, replacement, q)
            break
            
    # 3. Word replacements (check aliases)
    words = q.split(" ")
    new_words = []
    for w in words:
        # Check if word (stripped of punctuation/quotes) matches any alias
        clean_w = re.sub(r'[^a-z0-9]', '', w)
        if clean_w in WORD_ALIASES:
            new_words.append(WORD_ALIASES[clean_w])
        else:
            new_words.append(w)
            
    normalized = " ".join(new_words).strip()
    return normalized
