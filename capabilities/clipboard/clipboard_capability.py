import subprocess
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class ClipboardCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "clipboard"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = ["clipboard", "paste", "read clipboard", "what's in my clipboard", "copied text", "what did i copy"]
        if any(word in q for word in keywords):
            return Intent(
                capability=self.name,
                confidence=0.95,
                parameters={}
            )
        return None

    def execute(self, params: dict) -> CapabilityResult:
        try:
            # Read clipboard text using native pbpaste command on macOS
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
            clipboard_text = result.stdout
            
            message = mochi_voice.format_clipboard(clipboard_text)
            
            # Fire event
            event_bus.publish("CLIPBOARD_READ", content_length=len(clipboard_text))
            
            return CapabilityResult(
                success=True,
                data={"content": clipboard_text, "length": len(clipboard_text)},
                message=message
            )
        except Exception as e:
            event_bus.publish("CLIPBOARD_READ_FAILED", error=str(e))
            return CapabilityResult(
                success=False,
                data={"error": str(e)},
                message=f"Meow... I couldn't read your clipboard! (Error: {e}) 🐾"
            )
