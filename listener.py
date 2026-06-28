import time
from PyQt5.QtCore import QObject, pyqtSignal
from pynput import mouse, keyboard

class GlobalInputListener(QObject):
    # Thread-safe signals to communicate back to the PyQt main thread
    activity_detected = pyqtSignal()
    typing_detected = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_key_time = 0.0
        self.typing_threshold = 0.45  # Max seconds between keystrokes to count as rapid typing

    def start(self):
        # We start the listeners in background threads (pynput handles this automatically via start())
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_activity,
            on_click=self._on_mouse_activity,
            on_scroll=self._on_mouse_activity
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
        
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
        
        print("[Debug] Global mouse and keyboard listeners started in background threads.")

    def stop(self):
        # Gracefully stop pynput listener threads
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
        print("[Debug] Global input listeners stopped.")

    def _on_mouse_activity(self, *args):
        try:
            from PyQt5 import sip
            if sip.isdeleted(self):
                return
        except (ImportError, AttributeError):
            pass
        try:
            # Any mouse movement, click, or scroll is activity
            self.activity_detected.emit()
        except RuntimeError:
            pass

    def _on_key_press(self, key):
        try:
            from PyQt5 import sip
            if sip.isdeleted(self):
                return
        except (ImportError, AttributeError):
            pass
        try:
            # Trigger activity
            self.activity_detected.emit()
        except RuntimeError:
            pass
        
        # Calculate keypress frequency for typing detection
        current_time = time.time()
        time_diff = current_time - self.last_key_time
        self.last_key_time = current_time
        
        if time_diff < self.typing_threshold:
            try:
                # Emitted when keys are hit in rapid succession
                self.typing_detected.emit()
            except RuntimeError:
                pass
