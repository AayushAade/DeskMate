import sqlite3
from database import db_manager
from config import settings
from backends.ollama_backend import OllamaBackend

def save_session_summary(chat_history: list):
    """
    Summarizes the active chat session (chronological list of {"role", "text"})
    and saves the resulting summary to the SQLite database.
    """
    if not chat_history:
        return
        
    summary_text = ""
    
    # 1. Try to summarize using the local LLM
    if settings.ACTIVE_BACKEND == "ollama":
        try:
            backend = OllamaBackend()
            # Construct a special summarization prompt
            prompt_history = [
                {
                    "role": "user",
                    "text": (
                        f"Summarize the following conversation in one short sentence starting with 'User...' "
                        f"focusing on the main topics or tasks: \n\n"
                        f"{json_format_history(chat_history)}"
                    )
                }
            ]
            summary_text = backend.generate_response(prompt_history).strip()
        except Exception as e:
            print(f"[EpisodicMemory] LLM summarization failed, falling back to heuristics: {e}")
            
    # 2. Local heuristic fallback (if LLM is offline or failed)
    if not summary_text:
        summary_text = generate_heuristic_summary(chat_history)
        
    # 3. Store summary in DB
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO episodic_memory (summary) VALUES (?)", (summary_text,))
        conn.commit()
        print(f"[EpisodicMemory] Saved summary: '{summary_text}'")
    except sqlite3.Error as e:
        print(f"[EpisodicMemory] Error saving summary: {e}")
    finally:
        conn.close()

def get_episodic_memories(limit: int = 10) -> list:
    """Retrieves the list of high-level episodic memory summaries."""
    conn = db_manager.get_connection()
    summaries = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT summary, timestamp FROM episodic_memory ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        for row in rows:
            summaries.append({
                "summary": row["summary"],
                "timestamp": row["timestamp"]
            })
    except sqlite3.Error as e:
        print(f"[EpisodicMemory] Error loading memories: {e}")
    finally:
        conn.close()
    return summaries

def json_format_history(chat_history: list) -> str:
    """Formats chat history for LLM prompt ingestion."""
    formatted = []
    for msg in chat_history:
        sender = "User" if msg["role"] == "user" else "Mochi"
        formatted.append(f"{sender}: {msg['text']}")
    return "\n".join(formatted)

def generate_heuristic_summary(chat_history: list) -> str:
    """Generates a text summary using basic heuristics from user messages."""
    user_inputs = [msg["text"] for msg in chat_history if msg["role"] == "user"]
    if not user_inputs:
        return "User had a brief interaction with Mochi."
        
    # Heuristics based on keyword extraction
    actions = []
    for text in user_inputs:
        text_l = text.lower()
        if "calculate" in text_l or any(c in "+-*/^()" for c in text_l) and any(c.isdigit() for c in text_l):
            actions.append("calculations")
        if "weather" in text_l:
            actions.append("weather queries")
        if "search" in text_l or "google" in text_l:
            actions.append("web search")
        if "open" in text_l or "launch" in text_l:
            actions.append("opening apps")
        if "clipboard" in text_l or "paste" in text_l:
            actions.append("clipboard reads")
        if "file" in text_l or ".txt" in text_l or ".md" in text_l:
            actions.append("reading files")
            
    # De-duplicate
    actions = sorted(list(set(actions)))
    
    if len(actions) == 0:
        return f"User chatted with Mochi about general topics (including '{user_inputs[0][:30]}...')."
    elif len(actions) == 1:
        return f"User performed {actions[0]} with Mochi."
    else:
        return f"User did {', '.join(actions[:-1])} and {actions[-1]} with Mochi."
