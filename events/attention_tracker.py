import time
import math
import random
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication
from events import event_bus
from config.settings import log_info, log_debug, log_error

class AttentionTracker(QObject):
    # Signals to communicate attention events
    event_triggered = pyqtSignal(str, dict)

    def __init__(self, get_pet_geometry_cb=None, get_pet_facing_cb=None):
        super().__init__()
        self.get_pet_geometry = get_pet_geometry_cb
        self.get_pet_facing = get_pet_facing_cb  # Returns True if facing right, False if left

        # Active state parameters
        self.current_pos = (0, 0)
        self.prev_pos = (0, 0)
        self.velocity = 0.0
        self.interest = 50.0  # Starts neutral, bounded [0, 100]
        
        # Adaptive Polling Variables (lazily initialized on start() to prevent thread errors on import)
        self.poll_timer = None
        self.current_interval = 100
        
        # Proximity & Zone Proving
        self.last_move_time = time.time()
        self.time_in_zone = 0.0
        self.confidence_accumulated = 0.0  # seconds cursor has lingered in zone
        
        # Cooldown management
        self.last_event_times = {
            "CURSOR_FAST": 0.0,
            "CURSOR_SLOW": 0.0,
            "CURSOR_IDLE": 0.0,
            "CURSOR_HOVERING": 0.0
        }
        
        self.is_near = False
        self.is_hovering = False
        self.active_zone = "front"
        
        # Eye contact tracking
        self.eye_contact_decay_until = 0.0
        self.last_exit_direction = "front"

    def get_cursor_position(self) -> tuple:
        return self.current_pos

    def get_velocity(self) -> float:
        return self.velocity

    def get_interest(self) -> float:
        return self.interest

    def change_interest(self, delta: float):
        self.interest = max(0.0, min(100.0, self.interest + delta))

    def get_pet_center(self) -> tuple:
        """Returns the center (x, y) coordinates of the desktop pet."""
        if self.get_pet_geometry:
            geom = self.get_pet_geometry()
            return (geom.x() + geom.width() // 2, geom.y() + geom.height() // 2)
        # Fall back to screen center
        screen = QApplication.primaryScreen().geometry()
        return (screen.width() // 2, screen.height() // 2)

    def get_distance(self) -> float:
        cx, cy = self.get_pet_center()
        mx, my = self.current_pos
        return math.hypot(mx - cx, my - cy)

    def get_direction(self) -> str:
        """Classifies direction relative to Mochi's current facing direction."""
        cx, cy = self.get_pet_center()
        mx, my = self.current_pos
        
        # Calculate offsets
        dx = mx - cx
        dy = my - cy
        
        facing_right = self.get_pet_facing() if self.get_pet_facing is not None else True
        
        # Vertical check takes precedence if cursor is significantly above/below
        if dy < -60:
            return "above"
        elif dy > 60:
            return "below"
            
        if facing_right:
            return "front" if dx >= 0 else "behind"
        else:
            return "front" if dx < 0 else "behind"

    def check_proximity_ellipse(self, rx=220.0, ry=160.0) -> bool:
        """Evaluates proximity using an ellipse formula."""
        cx, cy = self.get_pet_center()
        mx, my = self.current_pos
        return ((mx - cx) ** 2) / (rx ** 2) + ((my - cy) ** 2) / (ry ** 2) <= 1.0

    def start(self):
        if self.poll_timer is None:
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(self.current_interval)

    def stop(self):
        if self.poll_timer is not None:
            self.poll_timer.stop()

    def poll(self):
        """Ticks the tracker: updates metrics, applies confidence/interest decays, and dispatches events."""
        now = time.time()
        pos = QCursor.pos()
        self.prev_pos = self.current_pos
        self.current_pos = (pos.x(), pos.y())
        
        dt = self.current_interval / 1000.0
        
        # Calculate velocity
        dx = self.current_pos[0] - self.prev_pos[0]
        dy = self.current_pos[1] - self.prev_pos[1]
        self.velocity = math.hypot(dx, dy) / dt
        
        # Update idle duration
        if self.velocity > 10.0:
            self.last_move_time = now
            idle_dur = 0.0
        else:
            idle_dur = now - self.last_move_time
            
        # Proximity Check (ellipse)
        inside = self.check_proximity_ellipse(220.0, 160.0)
        dist = self.get_distance()
        hovering = (dist <= 80.0)
        
        # Adjust adaptive polling interval
        # Hovering: 50ms, Proximity/Moving: 100ms, Idle/Far: 250ms
        target_interval = 250
        if inside:
            target_interval = 50 if hovering else 100
        elif self.velocity > 50.0:
            target_interval = 100
            
        if target_interval != self.current_interval:
            self.current_interval = target_interval
            if self.poll_timer is not None:
                self.poll_timer.setInterval(self.current_interval)
            
        # Proximity State transition
        if inside:
            # 1. Proximity Confidence check
            self.confidence_accumulated += dt
            self.time_in_zone += dt
            
            # Decay/Increment interest
            self.change_interest(5.0 * dt)
            
            if self.confidence_accumulated >= 0.3:  # lingered >= 300 ms
                if not self.is_near:
                    self.is_near = True
                    event_bus.publish("CURSOR_NEAR")
                    self.event_triggered.emit("CURSOR_NEAR", {})
                    
                # 2. Trigger hovering
                if hovering and not self.is_hovering:
                    self.is_hovering = True
                    if now - self.last_event_times["CURSOR_HOVERING"] >= 30.0:
                        self.last_event_times["CURSOR_HOVERING"] = now
                        event_bus.publish("CURSOR_HOVERING")
                        self.event_triggered.emit("CURSOR_HOVERING", {})
                elif not hovering:
                    self.is_hovering = False
                    
                # 3. High-velocity trigger (Startled)
                if self.velocity >= 1200.0:
                    if now - self.last_event_times["CURSOR_FAST"] >= 20.0:
                        self.last_event_times["CURSOR_FAST"] = now
                        event_bus.publish("CURSOR_FAST")
                        self.event_triggered.emit("CURSOR_FAST", {})
                        
                # 4. Slow cursor movement
                elif 50.0 <= self.velocity < 400.0:
                    if now - self.last_event_times["CURSOR_SLOW"] >= 10.0:
                        self.last_event_times["CURSOR_SLOW"] = now
                        event_bus.publish("CURSOR_SLOW")
                        self.event_triggered.emit("CURSOR_SLOW", {})
                        
                # 5. Proximity idle
                elif idle_dur >= 3.0:
                    if now - self.last_event_times["CURSOR_IDLE"] >= 10.0:
                        self.last_event_times["CURSOR_IDLE"] = now
                        event_bus.publish("CURSOR_IDLE")
                        self.event_triggered.emit("CURSOR_IDLE", {})
        else:
            # Cursor left proximity elliptical zone
            if self.is_near:
                self.is_near = False
                self.is_hovering = False
                self.time_in_zone = 0.0
                self.confidence_accumulated = 0.0
                self.last_exit_direction = self.get_direction()
                # Set eye contact decay window
                self.eye_contact_decay_until = now + random.uniform(0.5, 2.0)
                event_bus.publish("CURSOR_LEFT")
                self.event_triggered.emit("CURSOR_LEFT", {})
                
            self.confidence_accumulated = max(0.0, self.confidence_accumulated - dt)
            
        # Interest decay per second
        self.change_interest(-1.0 * dt)

# Instantiate the global tracker
tracker_instance = AttentionTracker()
