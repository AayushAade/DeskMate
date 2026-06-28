import re
from memory import semantic_memory, episodic_memory

# Stop words to ignore during keyword intersection scoring
STOP_WORDS = {"what", "who", "where", "how", "why", "is", "are", "do", "you", "me", "about", "the", "a", "an", "in", "on", "at", "for", "to", "i", "my"}

def tokenize(text: str) -> set:
    """Tokenizes string into lowercase alphanumeric words, filtering out stop words. Replaces underscores with spaces."""
    clean_text = text.replace('_', ' ')
    words = re.findall(r'\b[a-z0-9]+\b', clean_text.lower())
    return {w for w in words if w not in STOP_WORDS}

def retrieve_relevant_context(query: str, limit: int = 5) -> str:
    """
    Ranks stored memories against query and returns a formatted context block.
    Uses simple keyword intersection, memory type ranking, and recency.
    """
    query_tokens = tokenize(query)
    scored_memories = []
    
    if not query_tokens:
        # If query has no descriptive keywords, return general context (all facts)
        facts = semantic_memory.get_all_facts()
        if not facts:
            return ""
        lines = [f"- {k.replace('_', ' ').capitalize()}: {v}" for k, v in facts.items()]
        return "Relevant Facts:\n" + "\n".join(lines)

    # 1. Score Semantic Memories (Durable Facts)
    facts = semantic_memory.get_all_facts()
    for key, val in facts.items():
        fact_text = f"{key} {val}"
        fact_tokens = tokenize(fact_text)
        matches = query_tokens.intersection(fact_tokens)
        
        # Only include if there is a match
        if len(matches) > 0:
            score = len(matches) * 2.0 + 1.0  # Base score + match boost
            scored_memories.append({
                "type": "semantic",
                "content": f"User preference - {key.replace('_', ' ').capitalize()}: {val}",
                "score": score
            })
        
    # 2. Score Episodic Memories (Session Summaries)
    episodes = episodic_memory.get_episodic_memories(limit=30)
    for idx, ep in enumerate(episodes):
        ep_tokens = tokenize(ep["summary"])
        matches = query_tokens.intersection(ep_tokens)
        
        # Only include if there is a match
        if len(matches) > 0:
            score = len(matches) * 1.0
            # Recency boost (earlier index in ORDER BY DESC is newer)
            recency_boost = max(0.0, 1.0 - (idx * 0.05))
            score += recency_boost
            
            scored_memories.append({
                "type": "episodic",
                "content": f"Past exchange - {ep['summary']}",
                "score": score
            })

    # Sort memories by score DESC
    scored_memories.sort(key=lambda x: x["score"], reverse=True)
    
    # Filter out memories with zero score
    top_memories = [m for m in scored_memories if m["score"] > 0]
    
    # Take top N
    results = top_memories[:limit]
    if not results:
        # Fallback to general user facts if no match
        facts = semantic_memory.get_all_facts()
        if facts:
            lines = [f"User preference - {k.replace('_', ' ').capitalize()}: {v}" for k, v in facts.items()][:3]
            return "General context:\n" + "\n".join(lines)
        return ""
        
    lines = [m["content"] for m in results]
    return "Relevant Context:\n" + "\n".join(lines)
