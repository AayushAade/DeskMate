from PyQt5.QtCore import QObject, pyqtSignal

class TelemetryChannel(QObject):
    # Safe cross-thread signals for GUI updates
    routing_completed = pyqtSignal(dict)
    state_updated = pyqtSignal()

telemetry_channel = TelemetryChannel()
