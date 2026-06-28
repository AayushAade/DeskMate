import json
import urllib.request
import urllib.error
from backends.base_backend import BaseBackend
from config import settings
from assistant.personality.mochi_voice import SYSTEM_PROMPT

class OllamaBackend(BaseBackend):
    def __init__(self):
        self.url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    def generate_response(self, chat_history: list) -> str:
        # Construct system message
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]
        
        # Add conversation history
        for msg in chat_history:
            role = msg.get("role")
            ollama_role = "assistant" if role == "model" else "user"
            text = msg.get("text", "")
            
            messages.append({
                "role": ollama_role,
                "content": text
            })
            
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            # Timeout of 120 seconds
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data.get("message", {}).get("content", "")
                return content
                
        except urllib.error.URLError as e:
            print(f"[OllamaBackend] Connection error to Ollama: {e}")
            raise RuntimeError("I can't wake up right now... Is Ollama running? 🐾")
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                error_msg = err_json.get("error", str(e))
            except Exception:
                error_msg = str(e)
            raise RuntimeError(f"Ollama API Error: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Error: {e}")
