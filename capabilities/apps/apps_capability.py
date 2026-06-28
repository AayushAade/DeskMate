from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from services import app_service
from assistant.personality import mochi_voice
from events import event_bus

class AppsCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "apps"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        
        prefixes_open = ["open ", "launch ", "run "]
        prefixes_close = ["close ", "terminate ", "kill ", "stop "]
        
        matched = False
        action = "open"
        app_name = ""
        
        for prefix in prefixes_open:
            if q.startswith(prefix):
                matched = True
                action = "open"
                app_name = q[len(prefix):].strip()
                break
                
        for prefix in prefixes_close:
            if q.startswith(prefix):
                matched = True
                action = "close"
                app_name = q[len(prefix):].strip()
                break
                
        if matched and app_name:
            return Intent(
                capability=self.name,
                confidence=0.98,
                parameters={"app_name": app_name, "action": action}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        app_name = params.get("app_name", "").strip()
        action = params.get("action", "open")
        
        if action == "close":
            success, resolved_name, msg = app_service.close_app(app_name)
            if success:
                message = f"Mrrp! I've closed {resolved_name} for you! 🐾"
            else:
                message = f"Oh no, meow... I couldn't close {resolved_name}. 🐾"
            event_bus.publish("APP_CLOSED", app_name=resolved_name, success=success)
        else:
            success, resolved_name, msg = app_service.launch_app(app_name)
            message = mochi_voice.format_app_launch(resolved_name, success)
            event_bus.publish("APP_LAUNCHED", app_name=resolved_name, success=success)
            
        return CapabilityResult(
            success=success,
            data={"app_name": resolved_name, "action": action, "raw_message": msg},
            message=message
        )
