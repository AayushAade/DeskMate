import subprocess
import time
import random
from events import event_bus
from config import settings
from config.settings import log_info, log_debug, log_error
from assistant.state.state_manager import state_manager
from events.attention_tracker import tracker_instance

# Priority levels for scheduler interrupts
LOW = 1
NORMAL = 2
HIGH = 3
CRITICAL = 4

# Focus Mode Auto-Detection Tracker
_last_frontmost_app = None
_last_focus_check_time = 0.0

# Alert Trackers to prevent spamming
_battery_alerted = False
_unplugged_alerted = False

# Streak tracking for coding sessions (managed inside StateManager via typing checks)
_was_idle = False

class VariantDefinition:
    def __init__(self, name: str, min_duration: float, max_duration: float, interruptible: bool = True, sound: str = None):
        self.name = name
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.interruptible = interruptible
        self.sound = sound

class AnimationDefinition:
    def __init__(self, name: str, variants: list):
        self.name = name
        self.variants = variants

class Behavior:
    def __init__(self, name: str, base_weight: float, cooldown: float, priority: int, animations: list, conditions: list = None):
        self.name = name
        self.base_weight = base_weight
        self.cooldown = cooldown
        self.priority = priority
        self.animations = animations
        self.conditions = conditions or []
        self.last_run_time = 0.0

class BehaviorScheduler:
    def __init__(self):
        self.behaviors = {
            "relaxing": Behavior(
                "relaxing", base_weight=50.0, cooldown=0.0, priority=LOW,
                animations=[
                    AnimationDefinition("idle", [VariantDefinition("idle", 4.0, 9.0, interruptible=True)]),
                    AnimationDefinition("groom", [VariantDefinition("groom", 4.0, 7.0, interruptible=True)]),
                    AnimationDefinition("yawn", [VariantDefinition("yawn", 3.0, 4.0, interruptible=False, sound="yawn")]),
                    AnimationDefinition("stretch", [VariantDefinition("stretch", 4.0, 6.0, interruptible=False)])
                ]
            ),
            "curious": Behavior(
                "curious", base_weight=20.0, cooldown=10.0, priority=LOW,
                animations=[
                    AnimationDefinition("look_around", [
                        VariantDefinition("look_left", 3.0, 5.0, interruptible=True),
                        VariantDefinition("look_right", 3.0, 5.0, interruptible=True)
                    ]),
                    AnimationDefinition("tail_flick", [VariantDefinition("tail_flick", 2.0, 3.0, interruptible=True)])
                ]
            ),
            "sitting": Behavior(
                "sitting", base_weight=15.0, cooldown=15.0, priority=LOW,
                animations=[
                    AnimationDefinition("sit", [VariantDefinition("sit", 5.0, 8.0, interruptible=True)])
                ]
            ),
            "sleeping": Behavior(
                "sleeping", base_weight=10.0, cooldown=60.0, priority=NORMAL,
                animations=[
                    AnimationDefinition("sleep", [VariantDefinition("sleep", 12.0, 18.0, interruptible=False)])
                ],
                conditions=[self._is_sleepy_condition]
            ),
            "waking": Behavior(
                "waking", base_weight=0.0, cooldown=0.0, priority=NORMAL,
                animations=[
                    AnimationDefinition("wake", [VariantDefinition("wake", 3.0, 4.0, interruptible=False, sound="wake")])
                ],
                conditions=[self._is_waking_condition]
            ),
            "watching": Behavior(
                "watching", base_weight=0.0, cooldown=10.0, priority=LOW,
                animations=[
                    AnimationDefinition("look_around", [
                        VariantDefinition("look_left", 3.0, 5.0, interruptible=True),
                        VariantDefinition("look_right", 3.0, 5.0, interruptible=True),
                        VariantDefinition("look_up", 3.0, 5.0, interruptible=True)
                    ])
                ],
                conditions=[self._is_cursor_near_condition]
            ),
            "ignoring": Behavior(
                "ignoring", base_weight=0.0, cooldown=15.0, priority=LOW,
                animations=[
                    AnimationDefinition("idle", [VariantDefinition("idle", 4.0, 7.0, interruptible=True)])
                ]
            )
        }
        self.current_behavior = self.behaviors["relaxing"]
        self.current_animation = self.current_behavior.animations[0]
        self.current_variant = self.current_animation.variants[0]
        
        self.time_left = 5.0
        self.history = []  # last 3 behavior names
        self.blacklist = {}  # variant_name -> timestamp until available
        
        # Override state variables
        self.override_state = None
        self.override_priority = None
        self.override_duration = None
        
        # Idle pause tracking
        self.pause_time_left = 0.0
        
        # Debouncer tracking
        self.last_published_state = None
        
    def _is_sleepy_condition(self) -> bool:
        # Check if cursor is not near, and idle duration criteria is met
        if tracker_instance.is_near:
            return False
        return getattr(state_manager, "idle_seconds", 0) >= 60
        
    def _is_waking_condition(self) -> bool:
        return len(self.history) > 0 and self.history[-1] == "sleeping"

    def _is_cursor_near_condition(self) -> bool:
        return tracker_instance.is_near

    def request_override(self, state: str, priority: int, duration: float = None) -> bool:
        """Allows external systems (e.g. typing, thinking, low battery) to override pet behavior."""
        current_priority = self.override_priority or self.current_behavior.priority
        
        # If active variant is non-interruptible, check priority
        if self.current_variant and not self.current_variant.interruptible and priority < HIGH:
            return False
            
        if priority >= current_priority:
            self.override_state = state
            self.override_priority = priority
            self.override_duration = duration
            
            # Clear pause delay
            self.pause_time_left = 0.0
            
            # Set duration left to let override play immediately
            self.time_left = duration if duration is not None else 9999.0
            
            # Emit notifications
            if state != self.last_published_state:
                self.last_published_state = state
                event_bus.publish("BEHAVIOR_CHANGED", name=state, duration=self.time_left)
            event_bus.publish("ANIMATION_STARTED", name=state, metadata={"fps": 8, "loop": True})
            return True
        return False

    def release_override(self, state: str):
        """Releases the override if matching the requested state, reverting back to idle."""
        if self.override_state == state:
            self.override_state = None
            self.override_priority = None
            self.override_duration = None
            self.time_left = 0.0  # Force scheduler selection on next tick

    def tick_scheduler(self, is_idle: bool) -> str:
        """Ticks the scheduler. Returns the active variant name."""
        now = time.time()
        
        # Check override first
        if self.override_state:
            if self.override_duration is not None:
                self.override_duration -= 1.0
                if self.override_duration <= 0:
                    self.release_override(self.override_state)
            return self.override_state
            
        if not is_idle:
            # If not idle, force return to neutral idle when idle returns
            self.time_left = 0.0
            self.pause_time_left = 0.0
            return "idle"
            
        # If currently in a transition pause
        if self.pause_time_left > 0.0:
            self.pause_time_left -= 1.0
            return "idle"
            
        # If current variant still playing
        if self.time_left > 0.0:
            self.time_left -= 1.0
            return self.current_variant.name
            
        # 1. Variant finished. Introduce natural delay between behaviors (0.5s - 2.5s)
        self.pause_time_left = random.uniform(0.5, 2.5)
        
        # 2. Select next behavior
        valid_behaviors = []
        weights = []
        
        near = tracker_instance.is_near
        interest = tracker_instance.interest
        time_in_zone = tracker_instance.time_in_zone
        
        for name, b in self.behaviors.items():
            if name == "waking":
                if self._is_waking_condition():
                    valid_behaviors.append(b)
                    weights.append(100.0)
                continue
                
            if name == "sleeping" and len(self.history) > 0 and self.history[-1] == "waking":
                continue
                
            conds_pass = True
            for cond in b.conditions:
                if not cond():
                    conds_pass = False
                    break
            if not conds_pass:
                continue
                
            if now - b.last_run_time < b.cooldown:
                continue
                
            # Filter consecutive behavior repetitions
            weight = b.base_weight
            if len(self.history) > 0 and self.history[-1] == b.name:
                weight *= 0.1
                
            # Proximity Interest and Bored Progression Adjustments
            if near:
                if time_in_zone >= 20.0:
                    # Bored Progression: Look -> Flick -> Yawn -> Ignore
                    if b.name == "ignoring":
                        weight = 80.0
                    elif b.name == "relaxing":
                        # yawn is inside relaxing
                        weight = 20.0
                    else:
                        weight = 0.0
                else:
                    # Active interest scaling
                    if interest >= 60.0:
                        if b.name == "watching":
                            weight = interest * 1.5
                        elif b.name == "curious":
                            weight = interest * 1.0
                        elif b.name == "ignoring":
                            weight = 0.0
                    elif interest < 30.0:
                        if b.name == "ignoring":
                            weight = 60.0
                        elif b.name in ["watching", "curious"]:
                            weight = 10.0
            else:
                # Normal far weights
                if b.name in ["watching", "ignoring"]:
                    weight = 0.0
                
            # Energy scaling
            energy = getattr(state_manager, "energy", 80)
            if energy >= 60:
                if b.name == "curious":
                    weight *= 1.5
                elif b.name == "relaxing":
                    weight *= 1.2
            elif energy < 30:
                if b.name == "sitting":
                    weight *= 2.0
                elif b.name == "sleeping":
                    weight *= 3.0
                    
            if weight > 0.0:
                valid_behaviors.append(b)
                weights.append(weight)
            
        if not valid_behaviors:
            next_behavior = self.behaviors["relaxing"]
        else:
            next_behavior = random.choices(valid_behaviors, weights=weights, k=1)[0]
            
        # 3. Select animation inside behavior
        next_animation = random.choice(next_behavior.animations)
        
        # 4. Select variant inside animation (filtering recent blacklist)
        next_variant = None
        available_variants = []
        for v in next_animation.variants:
            if v.name not in self.blacklist or now >= self.blacklist[v.name]:
                available_variants.append(v)
                
        if not available_variants:
            next_variant = random.choice(next_animation.variants)
        else:
            next_variant = random.choice(available_variants)
            
        self.current_behavior = next_behavior
        self.current_animation = next_animation
        self.current_variant = next_variant
        
        self.current_behavior.last_run_time = now
        
        # Calculate random duration in range
        duration = random.uniform(self.current_variant.min_duration, self.current_variant.max_duration)
        self.time_left = duration
        
        # Add current variant to blacklist for 30 seconds
        self.blacklist[self.current_variant.name] = now + 30.0
        
        # Record history
        self.history.append(self.current_behavior.name)
        if len(self.history) > 3:
            self.history.pop(0)
            
        # Publish BEHAVIOR_CHANGED and ANIMATION_STARTED
        if self.current_variant.name != self.last_published_state:
            self.last_published_state = self.current_variant.name
            event_bus.publish("BEHAVIOR_CHANGED", name=self.current_variant.name, duration=self.time_left)
        
        meta = {
            "interruptible": self.current_variant.interruptible,
            "duration": self.time_left
        }
        if self.current_variant.sound:
            meta["sound"] = self.current_variant.sound
        event_bus.publish("ANIMATION_STARTED", name=self.current_variant.name, metadata=meta)
        
        return self.current_variant.name

# Instantiate the global behavior scheduler
scheduler_instance = BehaviorScheduler()

# Proximity event listeners to trigger immediate overrides
def _on_cursor_fast():
    # Startled trigger override
    scheduler_instance.request_override("surprised", NORMAL, duration=1.5)

def _on_cursor_hovering():
    # Playful swipe: 15% chance
    if random.random() < 0.15:
        scheduler_instance.request_override("paw_swipe", LOW, duration=2.0)

event_bus.subscribe("CURSOR_FAST", _on_cursor_fast)
event_bus.subscribe("CURSOR_HOVERING", _on_cursor_hovering)

def check_focus_mode_auto():
    """Runs a lightweight macOS AppleScript to check the frontmost process and toggle Focus Mode."""
    global _last_frontmost_app, _last_focus_check_time
    now = time.time()
    
    if now - _last_focus_check_time < 5.0:
        return
    _last_focus_check_time = now
    
    try:
        cmd = 'tell application "System Events" to name of first application process whose frontmost is true'
        result = subprocess.run(["osascript", "-e", cmd], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            app_name = result.stdout.strip()
            
            if app_name != _last_frontmost_app:
                _last_frontmost_app = app_name
                is_focus_app = any(app_name.lower() == fa.lower() for fa in settings.FOCUS_APPS)
                
                if is_focus_app:
                    if not state_manager.focus_mode:
                        state_manager.focus_mode = True
                        log_info(f"Auto Focus Mode ON: Active developer app '{app_name}' focused.")
                else:
                    if state_manager.focus_mode:
                        state_manager.focus_mode = False
                        log_info(f"Auto Focus Mode OFF: Active app '{app_name}' is not in allowlist.")
    except Exception as e:
        pass

def tick(idle_seconds: int, is_typing: bool) -> str | None:
    """
    Called every 1 second by the pet's behavior timer.
    Delegates ticks to state_manager, runs auto Focus checks, 
    drives the BehaviorScheduler, and handles proactive dialog updates.
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
    
    # 3. Tick BehaviorScheduler
    is_idle = (idle_seconds > 0) and not state_manager.is_thinking
    scheduler_instance.tick_scheduler(is_idle)
    
    # 4. Check for proactive alerts (suppressed if Focus Mode is Active)
    if state_manager.focus_mode:
        if is_typing:
            _was_idle = False
        return None
        
    if is_typing:
        if _was_idle:
            _was_idle = False
            state_manager.handle_event("USER_RETURNED")
            return "*waves paw*\n\nWelcome back! I kept your desktop safe. 😺"
            
        if state_manager.mood == "Sleepy":
            return "*yawns*\n\nI've been watching you code for a while... Maybe stretch a little? 🐾"
    else:
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
    
    if percent <= 15 and not charging:
        if not _battery_alerted:
            _battery_alerted = True
            if not state_manager.focus_mode:
                event_bus.publish("PROACTIVE_ALERT", message="*looks worried*\n\nYour battery's getting sleepy... Maybe find a charger? 🔋🐾", type="LOW_BATTERY")
    else:
        if percent > 20:
            _battery_alerted = False

    if not charging:
        if not _unplugged_alerted:
            _unplugged_alerted = True
            state_manager.handle_event("CHARGER_DISCONNECTED")
            if not state_manager.focus_mode:
                event_bus.publish("PROACTIVE_ALERT", message="*looks confused*\n\nWe're on battery power now! 🔌🐾", type="CHARGER_DISCONNECTED")
    else:
        if _unplugged_alerted:
            _unplugged_alerted = False
            state_manager.handle_event("CHARGER_CONNECTED")
            if not state_manager.focus_mode:
                event_bus.publish("PROACTIVE_ALERT", message="*happy hop*\n\nCharger connected! Nya! ⚡🐾", type="CHARGER_CONNECTED")

# Subscribe behavior engine to Event Bus
event_bus.subscribe("APP_LAUNCHED", _on_app_launched)
event_bus.subscribe("CALCULATION_COMPLETED", _on_calc_completed)
event_bus.subscribe("WEATHER_FETCHED", _on_weather_fetched)
event_bus.subscribe("BATTERY_CHECKED", _on_battery_checked)
