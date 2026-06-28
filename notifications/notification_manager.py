from PyQt5.QtCore import QObject, pyqtSignal
from events import event_bus

class NotificationManager(QObject):
    # Signal emitted to notify the UI of a reminder or proactive event
    # Signature: (title, message)
    notification_triggered = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        # Subscribe to Event Bus alert topics
        event_bus.subscribe("REMINDER_DUE", self._on_reminder_due)
        event_bus.subscribe("PROACTIVE_ALERT", self._on_proactive_alert)

    def _on_reminder_due(self, id: int, task: str):
        message = f"*rings bell*\n\nMrrp! Here is your reminder: **{task}**! 🔔🐾"
        self.notification_triggered.emit("🐾 Mochi Reminder", message)

    def _on_proactive_alert(self, message: str):
        self.notification_triggered.emit("🐾 Mochi Alert", message)

    def trigger_custom_notification(self, title: str, message: str):
        """Allows direct external triggers of notifications."""
        self.notification_triggered.emit(title, message)

# Instantiate a global notification manager instance for UI subscription
notification_manager = NotificationManager()
