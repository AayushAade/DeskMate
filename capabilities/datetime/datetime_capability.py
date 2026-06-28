from datetime import datetime
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class DateTimeCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "datetime"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = ["time", "date", "clock", "what day", "what today", "what's the time"]
        if any(word in q for word in keywords):
            return Intent(
                capability=self.name,
                confidence=0.90,
                parameters={}
            )
        return None

    def execute(self, params: dict) -> CapabilityResult:
        now = datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        time_str = now.strftime('%I:%M:%S %p')
        tz_str = now.astimezone().tzname() or "local"
        
        message = mochi_voice.format_datetime(date_str, time_str, tz_str)
        
        # Fire event
        event_bus.publish("DATETIME_ACCESSED", time_str=time_str, date_str=date_str)
        
        return CapabilityResult(
            success=True,
            data={"date": date_str, "time": time_str, "timezone": tz_str},
            message=message
        )
