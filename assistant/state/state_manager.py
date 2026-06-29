import time
from database import db_manager
from events import event_bus
from assistant.state.telemetry import telemetry_channel
from config.settings import log_info, log_error, log_debug

class AnimationProfile:
    def __init__(self, interval: int, probabilities: dict):
        self.interval = interval
        # Map sub-states to probabilities (must sum to 1.0)
        self.probabilities = probabilities

# Animation Profiles for each mood
MOOD_PROFILES = {
    "Relaxed": AnimationProfile(
        interval=120,
        probabilities={"idle": 0.70, "blink": 0.15, "tail_flick": 0.10, "clean_paw": 0.05}
    ),
    "Focused": AnimationProfile(
        interval=150,
        probabilities={"idle": 0.80, "blink": 0.10, "look_around": 0.10}
    ),
    "Sleepy": AnimationProfile(
        interval=240,
        probabilities={"idle": 0.65, "blink": 0.20, "stretch": 0.08, "yawn": 0.07}
    ),
    "Playful": AnimationProfile(
        interval=100,
        probabilities={"idle": 0.40, "tail_flick": 0.30, "hop": 0.20, "clean_paw": 0.10}
    ),
    "Curious": AnimationProfile(
        interval=110,
        probabilities={"idle": 0.50, "look_around": 0.30, "blink": 0.10, "tail_flick": 0.10}
    )
}

# Default profiles for temporary emotions if fallback profile is needed
EMOTION_PROFILES = {
    "Happy": AnimationProfile(interval=100, probabilities={"idle": 0.50, "tail_flick": 0.30, "hop": 0.20}),
    "Excited": AnimationProfile(interval=80, probabilities={"hop": 0.35, "tail_flick": 0.35, "idle": 0.15, "look_around": 0.15}),
    "Surprised": AnimationProfile(interval=90, probabilities={"hop": 0.50, "look_around": 0.50}),
    "Confused": AnimationProfile(interval=130, probabilities={"look_around": 0.70, "idle": 0.30}),
    "Worried": AnimationProfile(interval=140, probabilities={"idle": 0.60, "look_around": 0.40})
}

class StateManager:
    def __init__(self):
        # Long-lived state variables
        self.mood = "Relaxed"
        self.affection_level = "Stranger"
        self.energy = 80
        self.focus_mode = False
        
        # Short-lived state variables
        self.emotion = None
        self.emotion_timer = 0  # Number of tick seconds remaining for emotion
        
        # Runtime variables
        self.current_capability = None
        self.last_capability = None
        self.idle_seconds = 0
        self.is_typing = False
        self.is_thinking = False
        self.active_session_messages = 0
        self.active_typing_seconds = 0
        
        # Load persisted values
        self.load_persisted_state()
        self.update_affection()

    def load_persisted_state(self):
        """Loads state variables saved in the SQLite preferences table."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM preferences WHERE key IN ('mochi_mood', 'mochi_energy')")
            rows = cursor.fetchall()
            for row in rows:
                if row["key"] == "mochi_mood" and row["value"] in MOOD_PROFILES:
                    self.mood = row["value"]
                elif row["key"] == "mochi_energy":
                    try:
                        self.energy = int(row["value"])
                    except ValueError:
                        pass
        except Exception as e:
            log_error(f"Error loading persisted state: {e}")
        finally:
            conn.close()

    def persist_state(self):
        """Saves current mood and energy values to the preferences table."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES ('mochi_mood', ?)", (self.mood,))
            cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES ('mochi_energy', ?)", (str(self.energy),))
            conn.commit()
        except Exception as e:
            log_error(f"Error saving state: {e}")
        finally:
            conn.close()

    def update_affection(self):
        """
        Queries analytics tables to calculate engagement metrics and updates
        Mochi's affection level.
        Stranger: 0-30 interactions
        Acquaintance: 30-100 interactions
        Friend: 100-300 interactions AND >= 3 active days
        Companion: 300-1000 interactions AND >= 14 active days
        Best Friend: 1000+ interactions AND >= 60 active days
        """
        conn = db_manager.get_connection()
        total_interactions = 0
        active_days = 1
        try:
            cursor = conn.cursor()
            
            # Count total entries in usage_analytics (acts as interaction count)
            cursor.execute("SELECT COUNT(*) as count FROM usage_analytics")
            total_interactions = cursor.fetchone()["count"]
            
            # Count active days
            cursor.execute("SELECT COUNT(*) as count FROM active_days")
            active_days = max(1, cursor.fetchone()["count"])
            
        except Exception as e:
            log_error(f"Error loading affection analytics: {e}")
        finally:
            conn.close()
            
        old_level = self.affection_level
        
        # Calculate level
        if total_interactions < 30:
            self.affection_level = "Stranger"
        elif total_interactions < 100:
            self.affection_level = "Acquaintance"
        elif total_interactions < 300 or active_days < 3:
            self.affection_level = "Friend"
        elif total_interactions < 1000 or active_days < 14:
            self.affection_level = "Companion"
        else:
            self.affection_level = "Best Friend"
            
        if old_level != self.affection_level:
            event_bus.publish("AFFECTION_CHANGED", old_level=old_level, new_level=self.affection_level)
            log_info(f"Affection leveled up: {old_level} -> {self.affection_level}")

    def get_animation_profile(self) -> AnimationProfile:
        """Returns the current animation profile (uses emotion first, falls back to mood)."""
        if self.emotion and self.emotion in EMOTION_PROFILES:
            return EMOTION_PROFILES[self.emotion]
        return MOOD_PROFILES.get(self.mood, MOOD_PROFILES["Relaxed"])

    def handle_event(self, event_name: str, data: dict = None):
        """
        Centralized state transition handler.
        All event triggers flow through here to update emotion, mood, energy, and affection.
        """
        if data is None:
            data = {}
            
        old_mood = self.mood
        old_emotion = self.emotion
        
        if event_name == "USER_MESSAGE":
            self.active_session_messages += 1
            # Slight energy boost when interacting
            self.energy = min(100, self.energy + 2)
            # Upgrades affection check
            self.update_affection()
            
        elif event_name == "APP_LAUNCHED":
            success = data.get("success", True)
            if success:
                self.emotion = "Excited"
                self.emotion_timer = 30
                self.energy = max(0, self.energy - 4)
                
        elif event_name == "CALCULATION_COMPLETED":
            self.mood = "Focused"
            self.emotion = "Happy"
            self.emotion_timer = 15
            self.energy = max(0, self.energy - 2)
            
        elif event_name == "WEATHER_FETCHED" or event_name == "SEARCH_COMPLETED":
            self.mood = "Curious"
            self.energy = max(0, self.energy - 3)
            
        elif event_name == "BATTERY_CHECKED":
            percent = data.get("percent", 100)
            charging = data.get("charging", False)
            if percent <= 15 and not charging:
                self.emotion = "Worried"
                self.emotion_timer = 30
                self.mood = "Relaxed"
                
        elif event_name == "CHARGER_CONNECTED":
            self.emotion = "Excited"
            self.emotion_timer = 30
            self.energy = min(100, self.energy + 10)
            
        elif event_name == "CHARGER_DISCONNECTED":
            self.emotion = "Confused"
            self.emotion_timer = 20
            
        elif event_name == "REMINDER_ADDED":
            self.energy = max(0, self.energy - 1)
            
        elif event_name == "REMINDER_DUE":
            self.emotion = "Surprised"
            self.emotion_timer = 25
            self.energy = max(0, self.energy - 2)
            
        elif event_name == "USER_RETURNED":
            self.emotion = "Excited"
            self.emotion_timer = 30
            self.energy = min(100, self.energy + 5)
            
        elif event_name == "TICK":
            # Idle energy adjustments
            self.idle_seconds = data.get("idle_seconds", 0)
            self.is_typing = data.get("is_typing", False)
            self.is_thinking = data.get("is_thinking", False)
            
            # Decrement short-lived emotion timers
            if self.emotion:
                self.emotion_timer -= 1
                if self.emotion_timer <= 0:
                    self.emotion = None
                    self.emotion_timer = 0
                    
            # Drift energy based on state & track typing duration
            if self.is_typing:
                self.active_typing_seconds += 1
                if self.active_typing_seconds >= 20:
                    self.mood = "Sleepy"
                # Active work drains energy
                if int(time.time()) % 10 == 0:  # Every 10 seconds
                    self.energy = max(0, self.energy - 1)
            else:
                self.active_typing_seconds = max(0, self.active_typing_seconds - 1)
                # Rest restores energy
                if self.idle_seconds >= 30 and int(time.time()) % 15 == 0:
                    self.energy = min(100, self.energy + 1)
                    
            # Mood transitions based on idle metrics
            if self.idle_seconds >= 60:
                self.mood = "Sleepy"
            elif self.is_typing and self.mood == "Sleepy" and self.active_typing_seconds < 20:
                self.mood = "Relaxed"
                
        # Persist if long term metrics updated
        if self.mood != old_mood or self.emotion != old_emotion or event_name == "TICK":
            if self.mood != old_mood or self.emotion != old_emotion:
                self.persist_state()
            event_bus.publish("STATE_UPDATED")
            telemetry_channel.state_updated.emit()

# Singleton State Manager instance
state_manager = StateManager()
