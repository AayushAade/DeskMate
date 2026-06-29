import time
from PyQt5.QtCore import QObject, pyqtSignal
from events import event_bus
from config.settings import log_info, log_debug

class NotificationManager(QObject):
    # Signal emitted to notify the UI of a reminder or proactive event
    # Signature: (title, message)
    notification_triggered = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        # Subscribe to Event Bus alert topics
        event_bus.subscribe("REMINDER_DUE", self._on_reminder_due)
        event_bus.subscribe("PROACTIVE_ALERT", self._on_proactive_alert)
        self._cooldowns = {}  # Map type string -> timestamp of last occurrence

    def _on_reminder_due(self, id: int, task: str):
        # User-created reminders bypass cooldown checks
        message = f"*rings bell*\n\nMrrp! Here is your reminder: **{task}**! 🔔🐾"
        self.notification_triggered.emit("🐾 Mochi Reminder", message)

    def _on_proactive_alert(self, message: str, type: str = "GENERAL_PROACTIVE"):
        from assistant.state.state_manager import state_manager
        if state_manager.focus_mode:
            log_debug(f"Suppressed proactive alert type '{type}' because Focus Mode is active.")
            return
            
        now = time.time()
        if type in self._cooldowns:
            elapsed = now - self._cooldowns[type]
            if elapsed < 600:  # 10 minutes cooldown
                log_debug(f"Suppressed duplicate proactive alert of type '{type}' (cooldown active: {600 - elapsed:.1f}s remaining)")
                return
                
        self._cooldowns[type] = now
        self.notification_triggered.emit("🐾 Mochi Alert", message)

    def trigger_custom_notification(self, title: str, message: str, type: str = "GENERAL_PROACTIVE"):
        """Allows direct external triggers of notifications with optional type cooldowns."""
        from assistant.state.state_manager import state_manager
        if type != "REMINDER" and state_manager.focus_mode:
            log_debug(f"Suppressed custom proactive alert type '{type}' because Focus Mode is active.")
            return
            
        now = time.time()
        if type != "REMINDER":
            if type in self._cooldowns:
                elapsed = now - self._cooldowns[type]
                if elapsed < 600:
                    log_debug(f"Suppressed duplicate custom alert of type '{type}' (cooldown active)")
                    return
            self._cooldowns[type] = now
            
        self.notification_triggered.emit(title, message)

# Instantiate a global notification manager instance for UI subscription
notification_manager = NotificationManager()
