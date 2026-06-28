import subprocess
import re
import psutil
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class BatteryCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "battery"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = ["battery", "charge", "power status", "remaining power", "power level"]
        if any(word in q for word in keywords):
            return Intent(
                capability=self.name,
                confidence=0.95,
                parameters={}
            )
        return None

    def _parse_pmset(self) -> tuple:
        """Runs pmset -g batt and parses details on macOS."""
        try:
            result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            # Find percent
            percent_match = re.search(r'(\d+)%', output)
            if not percent_match:
                return None
            percent = int(percent_match.group(1))
            
            # Find charging state
            charging = False
            if "charging" in output and "discharging" not in output:
                charging = True
            elif "AC Power" in output:
                # Connected to charger and charged or finishing charge
                charging = True
                
            # Find remaining time
            time_match = re.search(r'(\d+:\d+)\s+remaining', output)
            time_left = time_match.group(1) if time_match else "unknown"
            if "charged" in output:
                time_left = "charged"
                
            return percent, charging, time_left
        except Exception:
            return None

    def execute(self, params: dict) -> CapabilityResult:
        # 1. Try pmset -g batt
        parsed = self._parse_pmset()
        
        if parsed:
            percent, charging, time_left = parsed
        else:
            # 2. Fallback to psutil
            try:
                batt = psutil.sensors_battery()
                if batt:
                    percent = int(batt.percent)
                    charging = batt.power_plugged
                    if batt.secsleft == psutil.POWER_TIME_UNLIMITED:
                        time_left = "unlimited"
                    elif batt.secsleft == psutil.POWER_TIME_UNKNOWN:
                        time_left = "unknown"
                    else:
                        hours = int(batt.secsleft // 3600)
                        mins = int((batt.secsleft % 3600) // 60)
                        time_left = f"{hours}:{mins:02d}"
                else:
                    raise ValueError("No battery device found")
            except Exception as e:
                # Total fallback if no battery device at all (e.g. desktop Mac)
                event_bus.publish("BATTERY_CHECK_FAILED", error=str(e))
                return CapabilityResult(
                    success=False,
                    data={"error": str(e)},
                    message="Meow... I couldn't read the battery. Are we plugged into a wall outlet? 🐾"
                )

        message = mochi_voice.format_battery(percent, charging, time_left)
        
        # Fire event
        event_bus.publish("BATTERY_CHECKED", percent=percent, charging=charging, time_left=time_left)
        
        return CapabilityResult(
            success=True,
            data={"percent": percent, "charging": charging, "time_left": time_left},
            message=message
        )
