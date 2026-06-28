import subprocess
import time
from events import event_bus
from config import settings
from assistant.state.state_manager import state_manager

# Focus Mode Auto-Detection Tracker
_last_frontmost_app = None
_last_focus_check_time = 0.0

# Alert Trackers to prevent spamming
_battery_alerted = False
_unplugged_alerted = False

# Streak tracking for coding sessions (managed inside StateManager via typing checks)
_was_idle = False

def check_focus_mode_auto():
    """Runs a lightweight macOS AppleScript to check the frontmost process and toggle Focus Mode."""
    global _last_frontmost_app, _last_focus_check_time
    now = time.time()
    
    # Run check at most once every 5 seconds to keep CPU overhead at 0.00%
    if now - _last_focus_check_time < 5.0:
        return
    _last_focus_check_time = now
    
    try:
        # Fast AppleScript to fetch frontmost process name
        cmd = 'tell application "System Events" to name of first application process whose frontmost is true'
        result = subprocess.run(["osascript", "-e", cmd], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            app_name = result.stdout.strip()
            
            if app_name != _last_frontmost_app:
                _last_frontmost_app = app_name
                # Check case-insensitive against allowlist
                is_focus_app = any(app_name.lower() == fa.lower() for fa in settings.FOCUS_APPS)
                
                if is_focus_app:
                    if not state_manager.focus_mode:
                        state_manager.focus_mode = True
                        print(f"[BehaviorEngine] Auto Focus Mode ON: Active developer app '{app_name}' focused.")
                else:
                    if state_manager.focus_mode:
                        state_manager.focus_mode = False
                        print(f"[BehaviorEngine] Auto Focus Mode OFF: Active app '{app_name}' is not in allowlist.")
    except Exception as e:
        # Ignore errors if system events are busy
        pass

def tick(idle_seconds: int, is_typing: bool) -> str | None:
    """
    Called every 1 second by the pet's behavior timer.
    Delegates ticks to state_manager, runs auto Focus checks, 
    and handles proactive dialog updates.
    """
    global _was_idle
    
    # 1. Update State Manager values
    state_manager.handle_event("TICK", {
        "idle_seconds": idle_seconds, 
        "is_typing": is_typing,
        "is_thinking": state_manager.is_thinking
    })
    
    # 2. Focus Auto-Detection
    check_focus_mode_auto()
    
    # 3. Check for proactive alerts (suppressed if Focus Mode is Active)
    if state_manager.focus_mode:
        # Reset tracking but yield nothing (distraction-free)
        if is_typing:
            _was_idle = False
        return None
        
    # User is not in Focus Mode - evaluate proactive alerts
    if is_typing:
        if _was_idle:
            _was_idle = False
            state_manager.handle_event("USER_RETURNED")
            return "*waves paw*\n\nWelcome back! I kept your desktop safe. 😺"
            
        # Check active session interactions / coding time
        if state_manager.mood == "Sleepy":
            return "*yawns*\n\nI've been watching you code for a while... Maybe stretch a little? 🐾"
    else:
        # Check idle returns
        if idle_seconds >= 60:
            _was_idle = True
            
    return None

# Event listeners to forward triggers to StateManager
def _on_app_launched(app_name, success):
    state_manager.handle_event("APP_LAUNCHED", {"app_name": app_name, "success": success})

def _on_calc_completed(expression, result):
    state_manager.handle_event("CALCULATION_COMPLETED", {"expression": expression, "result": result})

def _on_weather_fetched(weather_info):
    state_manager.handle_event("WEATHER_FETCHED", weather_info)

def _on_battery_checked(percent, charging, time_left):
    global _battery_alerted, _unplugged_alerted
    state_manager.handle_event("BATTERY_CHECKED", {"percent": percent, "charging": charging})
    
    # Critical alerts bypass Focus Mode suppression to protect user's work
    if percent <= 15 and not charging:
        if not _battery_alerted:
            _battery_alerted = True
            event_bus.publish("PROACTIVE_ALERT", message="*looks worried*\n\nYour battery's getting sleepy... Maybe find a charger? 🔋🐾")
    else:
        if percent > 20:
            _battery_alerted = False

    # Charging cable alerts
    if not charging:
        if not _unplugged_alerted:
            _unplugged_alerted = True
            state_manager.handle_event("CHARGER_DISCONNECTED")
            event_bus.publish("PROACTIVE_ALERT", message="*looks confused*\n\nWe're on battery power now! 🔌🐾")
    else:
        if _unplugged_alerted:
            _unplugged_alerted = False
            state_manager.handle_event("CHARGER_CONNECTED")
            event_bus.publish("PROACTIVE_ALERT", message="*happy hop*\n\nCharger connected! Nya! ⚡🐾")

# Subscribe behavior engine to Event Bus
event_bus.subscribe("APP_LAUNCHED", _on_app_launched)
event_bus.subscribe("CALCULATION_COMPLETED", _on_calc_completed)
event_bus.subscribe("WEATHER_FETCHED", _on_weather_fetched)
event_bus.subscribe("BATTERY_CHECKED", _on_battery_checked)
