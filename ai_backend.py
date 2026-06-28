from PyQt5.QtCore import QThread, pyqtSignal
from assistant.router.router import AssistantRouter
from memory import semantic_memory, policy
from database import db_manager

# Instantiate the AssistantRouter
assistant_router = AssistantRouter()

class AIWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, chat_history):
        super().__init__()
        # chat_history format: [{"role": "user"|"model", "parts": [{"text": text}]}]
        self.chat_history = chat_history

    def run(self):
        # 1. Extract the latest user query
        user_query = ""
        if self.chat_history:
            last_msg = self.chat_history[-1]
            if last_msg.get("role") == "user":
                parts = last_msg.get("parts", [])
                user_query = parts[0].get("text", "") if parts else ""
                
        if not user_query:
            self.error.emit("Meow? I didn't hear anything... 🐾")
            return
            
        # 2. Analyze query via Memory Policy (Semantic facts or direct episodic statements)
        try:
            mem_type, key, val = policy.analyze_input(user_query)
            if mem_type == "semantic":
                semantic_memory.save_fact(key, val)
                print(f"[AIWorker] Extracted fact: {key} -> {val}")
            elif mem_type == "episodic":
                # Save direct accomplishments immediately
                conn = db_manager.get_connection()
                conn.execute("INSERT INTO episodic_memory (summary) VALUES (?)", (val,))
                conn.commit()
                conn.close()
                print(f"[AIWorker] Saved accomplishment: {val}")
        except Exception as e:
            print(f"[AIWorker] Memory policy analysis exception: {e}")
            
        # 3. Map working memory chat history to simple format
        mapped_history = []
        for msg in self.chat_history:
            role = msg.get("role")
            parts = msg.get("parts", [])
            text = parts[0].get("text", "") if parts else ""
            mapped_history.append({
                "role": role,
                "text": text
            })
            
        # 4. Route and execute through the AssistantRouter
        try:
            response_text = assistant_router.route_and_execute(user_query, mapped_history)
            self.finished.emit(response_text)
        except Exception as e:
            error_str = str(e)
            print(f"[AIWorker] Exception during routing: {e}")
            if "wake up" in error_str or "connection" in error_str.lower():
                self.error.emit("I can't wake up right now... Is Ollama running? 🐾")
            else:
                self.error.emit(f"Error: {error_str}")
