import re
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from services import scheduler

class RemindersCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "reminders"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        
        # Regex matching phrases like: "remind me to stretch in 10 seconds" or "set reminder to stretch in 5 minutes"
        pattern = r'(?:remind me to|remind me|set a reminder to|set reminder for)\s+(.+?)\s+in\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours)'
        match = re.search(pattern, q)
        
        if match:
            task = match.group(1).strip()
            amount = int(match.group(2))
            unit = match.group(3).strip()
            
            # Convert units to seconds
            delay = amount
            if "minute" in unit:
                delay = amount * 60
            elif "hour" in unit:
                delay = amount * 3600
                
            return Intent(
                capability=self.name,
                confidence=0.98,
                parameters={"task": task, "delay_seconds": delay, "original_unit": unit, "original_amount": amount}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        task = params.get("task", "")
        delay_seconds = params.get("delay_seconds", 0)
        amount = params.get("original_amount", delay_seconds)
        unit = params.get("original_unit", "seconds")
        
        reminder_id = scheduler.add_reminder(task, delay_seconds)
        
        if reminder_id != -1:
            message = f"Mrrp! I've set a reminder to **{task}** in {amount} {unit}! 🔔🐾"
            success = True
        else:
            message = "Oh no, meow... I couldn't set that reminder. 🐾"
            success = False
            
        return CapabilityResult(
            success=success,
            data={"reminder_id": reminder_id, "task": task, "delay_seconds": delay_seconds},
            message=message
        )
