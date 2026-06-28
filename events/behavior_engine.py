from events import event_bus

# Current pet mood state
_mood = "Happy"
_active_typing_seconds = 0
_was_idle = False

# Battery alert tracker to avoid spamming alerts
_battery_alerted = False
_unplugged_alerted = False

def get_mood() -> str:
    """Returns Mochi's current mood."""
    return _mood

def set_mood(new_mood: str):
    """Sets a new mood and publishes a MOOD_CHANGED event on the Event Bus."""
    global _mood
    if _mood != new_mood:
        old_mood = _mood
        _mood = new_mood
        event_bus.publish("MOOD_CHANGED", old_mood=old_mood, new_mood=new_mood)
        print(f"[BehaviorEngine] Mood changed: {old_mood} -> {new_mood}")

def tick(idle_seconds: int, is_typing: bool) -> str | None:
    """
    Called every 1 second by the pet's behavior timer.
    Tracks typing duration, idle state returns, and triggers proactive alerts.
    Returns: A proactive message string if triggered, else None.
    """
    global _active_typing_seconds, _was_idle
    
    # 1. Track user activity / typing duration
    if is_typing:
        _active_typing_seconds += 1
        # Reset idle state
        if _was_idle:
            _was_idle = False
            set_mood("Excited")
            return "*waves paw*\n\nWelcome back! I kept your desktop safe. 😺"
            
        # Coding duration threshold: 2 hours (7200s), but for testing let's set to 20s
        if _active_typing_seconds == 20: # Trigger stretch reminder
            set_mood("Sleepy")
            return "*yawns*\n\nI've been watching you code for a while... Maybe stretch a little? 🐾"
    else:
        # User is not typing
        if _active_typing_seconds > 0:
            _active_typing_seconds = max(0, _active_typing_seconds - 1)
            
        # Idle check: more than 60s
        if idle_seconds >= 60:
            if not _was_idle:
                _was_idle = True
                set_mood("Sleepy")
                
    return None

# Event listeners to dynamically shift Mochi's mood
def _on_app_launched(app_name, success):
    if success:
        set_mood("Excited")

def _on_calc_completed(expression, result):
    set_mood("Focused")

def _on_weather_fetched(weather_info):
    set_mood("Curious")

def _on_battery_checked(percent, charging, time_left):
    global _battery_alerted, _unplugged_alerted
    
    if percent <= 15 and not charging:
        set_mood("Worried")
        if not _battery_alerted:
            _battery_alerted = True
            # Return/trigger alert via bus or notification manager
            event_bus.publish("PROACTIVE_ALERT", message="*looks worried*\n\nYour battery's getting sleepy... Maybe find a charger? 🔋🐾")
    else:
        # Reset alert
        if percent > 20:
            _battery_alerted = False

    # Charger connected/disconnected check
    if not charging:
        if not _unplugged_alerted:
            _unplugged_alerted = True
            set_mood("Confused")
            event_bus.publish("PROACTIVE_ALERT", message="*looks confused*\n\nWe're on battery power now! 🔌🐾")
    else:
        if _unplugged_alerted:
            _unplugged_alerted = False
            set_mood("Excited")
            event_bus.publish("PROACTIVE_ALERT", message="*happy hop*\n\nCharger connected! Nya! ⚡🐾")

# Subscribe listeners to the Event Bus
event_bus.subscribe("APP_LAUNCHED", _on_app_launched)
event_bus.subscribe("CALCULATION_COMPLETED", _on_calc_completed)
event_bus.subscribe("WEATHER_FETCHED", _on_weather_fetched)
event_bus.subscribe("BATTERY_CHECKED", _on_battery_checked)
