from PyQt5.QtCore import QThread, pyqtSignal
from assistant.router.router import AssistantRouter
from services import memory_service

# Instantiate the AssistantRouter
assistant_router = AssistantRouter()

class AIWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, chat_history):
        super().__init__()
        # Format of chat_history: [{"role": "user"|"model", "parts": [{"text": text}]}]
        self.chat_history = chat_history

    def run(self):
        # 1. Extract the latest user query to inspect/execute
        user_query = ""
        if self.chat_history:
            last_msg = self.chat_history[-1]
            if last_msg.get("role") == "user":
                parts = last_msg.get("parts", [])
                user_query = parts[0].get("text", "") if parts else ""
                
        if not user_query:
            self.error.emit("Meow? I didn't hear anything... 🐾")
            return
            
        # 2. Save user query to persistent SQLite memory
        session_id = "default_session"
        memory_service.save_chat_message(session_id, "user", user_query)
        
        # 3. Map PyQt chat_history list to simple list of {"role", "text"} for the Router
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
            
            # Save Mochi's response to persistent SQLite memory
            memory_service.save_chat_message(session_id, "model", response_text)
            
            # Emit result back to GUI
            self.finished.emit(response_text)
            
        except Exception as e:
            # Handle connection or internal runtime exceptions gracefully
            error_str = str(e)
            print(f"[AIWorker] Exception during routing: {e}")
            if "wake up" in error_str or "connection" in error_str.lower():
                self.error.emit("I can't wake up right now... Is Ollama running? 🐾")
            else:
                self.error.emit(f"Error: {error_str}")
