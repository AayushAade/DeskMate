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
        
        prefixes = ["open ", "launch ", "run "]
        matched = False
        app_name = ""
        
        for prefix in prefixes:
            if q.startswith(prefix):
                matched = True
                app_name = q[len(prefix):].strip()
                break
                
        if matched and app_name:
            return Intent(
                capability=self.name,
                confidence=0.98,
                parameters={"app_name": app_name}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        app_name = params.get("app_name", "").strip()
        
        success, resolved_name, msg = app_service.launch_app(app_name)
        message = mochi_voice.format_app_launch(resolved_name, success)
        
        # Fire event
        event_bus.publish("APP_LAUNCHED", app_name=resolved_name, success=success)
        
        return CapabilityResult(
            success=success,
            data={"app_name": resolved_name, "raw_message": msg},
            message=message
        )
