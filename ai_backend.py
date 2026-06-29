from PyQt5.QtCore import QThread, pyqtSignal
from assistant.router.router import AssistantRouter, RouterResult
from memory import semantic_memory, policy
from database import db_manager
from config.settings import log_info, log_error, log_debug

# Instantiate the AssistantRouter
assistant_router = AssistantRouter()

class AIWorker(QThread):
    finished = pyqtSignal(str)
    token_received = pyqtSignal(str)  # Emitted for each incoming token chunk
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
            
        # 2. Analyze query via Memory Policy
        try:
            mem_type, key, val = policy.analyze_input(user_query)
            if mem_type == "semantic":
                semantic_memory.save_fact(key, val)
                log_info(f"Extracted fact: {key} -> {val}")
            elif mem_type == "episodic":
                # Save direct accomplishments immediately
                conn = db_manager.get_connection()
                conn.execute("INSERT INTO episodic_memory (summary) VALUES (?)", (val,))
                conn.commit()
                conn.close()
                log_info(f"Saved accomplishment: {val}")
        except Exception as e:
            log_error(f"Memory policy analysis exception: {e}")
            
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
            
        # 4. Route and stream through the AssistantRouter
        try:
            full_response = []
            result_obj = None
            
            for chunk in assistant_router.route_and_stream(user_query, mapped_history):
                if isinstance(chunk, RouterResult):
                    result_obj = chunk
                else:
                    full_response.append(chunk)
                    self.token_received.emit(chunk)
                    
            if result_obj is None:
                # Fallback safeguard
                response_text = "".join(full_response)
                result_obj = RouterResult(success=True, response=response_text, source="fallback_safeguard")
                
            if result_obj.success:
                # Ensure the client gets the full resolved response
                self.finished.emit(result_obj.response)
            else:
                error_str = result_obj.error
                log_error(f"Routing outcome returned failure: {error_str}")
                if "connection" in error_str.lower() or "wake up" in error_str.lower() or "11434" in error_str:
                    self.error.emit("I can't wake up right now... Is Ollama running? 🐾")
                else:
                    self.error.emit(f"Error: {error_str}")
            
        except Exception as e:
            error_str = str(e)
            log_error(f"Exception during routing: {e}")
            if "connection" in error_str.lower() or "wake up" in error_str.lower() or "11434" in error_str:
                self.error.emit("I can't wake up right now... Is Ollama running? 🐾")
            else:
                self.error.emit(f"Error: {error_str}")
