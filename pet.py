import os
import re
from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QPushButton, 
                             QHBoxLayout, QVBoxLayout, QLineEdit, QFrame, QTextBrowser, QMenu)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter
from listener import GlobalInputListener
from ai_backend import AIWorker
from notifications.notification_manager import notification_manager
from events.behavior_engine import tick as behavior_tick
from services import scheduler
from assistant.state.state_manager import state_manager
from assistant.state.telemetry import telemetry_channel
from datetime import datetime
import random
from config.settings import log_info, log_error, log_debug
from events import event_bus

class AIAssistantChat(QWidget):
    def __init__(self, parent=None, parent_pet=None):
        super().__init__(parent)
        self.parent_pet = parent_pet
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Chat history lists
        self.chat_history = []
        self.display_history = []
        self.worker = None
        self.last_telemetry = None
        
        # Streaming and Refresh queue state variables
        self.is_streaming = False
        self.streaming_buffer = ""
        self.streaming_timer = QTimer(self)
        self.streaming_timer.timeout.connect(self._on_streaming_timer_tick)
        
        self.refresh_pending = False
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._on_refresh_timer_tick)
        
        self._updating_ui = False
        self.geometry_locked = False
        
        # Metrics
        self.metrics_refresh_requests = 0
        self.metrics_actual_repaints = 0
        self.metrics_avg_rebuild_time = 0.0
        
        self.init_ui()
        
        # Connect to Telemetry Channel signals
        telemetry_channel.routing_completed.connect(self.on_routing_completed)
        telemetry_channel.state_updated.connect(self.update_state_view)
        
        # Initial help text & Dev view
        self.show_system_message("Welcome to Mochi's corner! Click the cat or type below to chat. 🐾")
        self.update_state_view()

    def init_ui(self):
        # Root layout to contain main chat and developer diagnostics side-by-side
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)
        
        # 1. Container frame for cat-themed warm rose/cream styling (Main Chat)
        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setFixedWidth(320)
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: #fffafb;
                border: 2px solid #ffe4e6;
                border-radius: 16px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)
        
        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)
        
        self.title_label = QLabel("🐾 Mochi Chat", self)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #9f1239; 
                font-size: 13px; 
                font-weight: bold; 
                font-family: 'Chalkboard SE', 'Comic Sans MS', -apple-system, sans-serif;
            }
        """)
        
        self.btn_close = QPushButton("×", self)
        self.btn_close.setObjectName("close_btn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton#close_btn {
                background-color: transparent;
                color: #fda4af;
                border: none;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton#close_btn:hover {
                color: #f43f5e;
            }
        """)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        
        # Chat display area
        self.chat_display = QTextBrowser(self)
        self.chat_display.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #4c0519;
                font-family: 'Chalkboard SE', 'Comic Sans MS', -apple-system, sans-serif;
                font-size: 12px;
            }
            QScrollBar:vertical {
                border: none;
                background: #fff0f2;
                width: 6px;
                margin: 2px 0 2px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #fecdd3;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #fda4af;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
            }
        """)
        self.chat_display.setOpenExternalLinks(True)
        
        # Input block
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Say meow to Mochi...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #4c0519;
                border: 2px solid #ffe4e6;
                border-radius: 15px;
                padding: 6px 12px;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QLineEdit:focus {
                border: 2px solid #fda4af;
            }
        """)
        
        self.btn_send = QPushButton("Meow", self)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #f43f5e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QPushButton:hover {
                background-color: #e11d48;
            }
            QPushButton:pressed {
                background-color: #be123c;
            }
        """)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.btn_send)
        
        # Assemble container layout
        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.chat_display)
        container_layout.addLayout(input_layout)
        
        root_layout.addWidget(self.container)
        
        # 2. Developer Diagnostics Panel Frame (Collapsible Drawer)
        self.dev_panel = QFrame(self)
        self.dev_panel.setObjectName("dev_panel")
        self.dev_panel.setFixedWidth(280)
        self.dev_panel.setStyleSheet("""
            QFrame#dev_panel {
                background-color: #1e1e1e;
                border: 2px solid #333333;
                border-radius: 16px;
            }
        """)
        
        dev_layout = QVBoxLayout(self.dev_panel)
        dev_layout.setContentsMargins(12, 12, 12, 12)
        dev_layout.setSpacing(6)
        
        dev_title = QLabel("🛠️ Mochi Diagnostics", self)
        dev_title.setStyleSheet("QLabel { color: #f43f5e; font-size: 13px; font-weight: bold; font-family: monospace; }")
        dev_layout.addWidget(dev_title)
        
        self.dev_display = QTextBrowser(self)
        self.dev_display.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 11px;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 3px;
            }
        """)
        dev_layout.addWidget(self.dev_display)
        
        root_layout.addWidget(self.dev_panel)
        
        # Collapsed by default
        self.dev_panel.hide()
        self.setFixedSize(320, 420)
        
        # Connections
        self.btn_close.clicked.connect(self.hide)
        self.btn_send.clicked.connect(self.send_message)
        self.message_input.returnPressed.connect(self.send_message)

    def send_message(self):
        query = self.message_input.text().strip()
        if not query:
            return
            
        self.message_input.clear()
        self.append_message("user", query)
        
        self.chat_history.append({"role": "user", "parts": [{"text": query}]})
        
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
            
        self.show_thinking()
        
        self.message_input.setEnabled(False)
        self.btn_send.setEnabled(False)
        
        # Trigger parent pet to start typing (thinking animation)
        if self.parent_pet:
            self.parent_pet.is_thinking = True
            from events.behavior_engine import scheduler_instance, HIGH
            scheduler_instance.request_override("typing", HIGH)
            
        self.is_streaming = False
        
        # Spawn Ollama worker
        self.worker = AIWorker(self.chat_history)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.token_received.connect(self.on_token_received)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()

    def show_thinking(self):
        self.chat_display.append(f"""
            <div id="thinking" style="margin: 8px 0; text-align: left;">
                <span style="background-color: #ffffff; color: #fda4af; border: 1px solid #ffe4e6; border-radius: 12px 12px 12px 2px; padding: 8px 12px; display: inline-block;">
                    <b>🐾 Mochi</b><br/>*scratching ears* thinking...
                </span>
            </div>
        """)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def request_ui_refresh(self):
        self.metrics_refresh_requests += 1
        if not self.refresh_pending:
            self.refresh_pending = True
            self.refresh_timer.start(50)  # coalesced: fires once after 50ms

    def _on_refresh_timer_tick(self):
        self.refresh_timer.stop()
        self.refresh_pending = False
        self.rebuild_display()

    def _on_streaming_timer_tick(self):
        if self.streaming_buffer:
            if self.display_history:
                role, text = self.display_history[-1]
                if role == "model":
                    self.display_history[-1] = (role, text + self.streaming_buffer)
            self.streaming_buffer = ""
            self.request_ui_refresh()

    def on_token_received(self, token):
        if not self.is_streaming:
            self.is_streaming = True
            self.geometry_locked = True
            self.display_history.append(("model", ""))
            self.streaming_buffer = ""
            self.streaming_timer.start(100)  # Capped: refresh token text block buffer every 100ms
            
        self.streaming_buffer += token

    def on_worker_finished(self, response_text):
        self.message_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.message_input.setFocus()
        
        self.streaming_timer.stop()
        
        if self.parent_pet:
            self.parent_pet.is_thinking = False
            from events.behavior_engine import scheduler_instance
            scheduler_instance.release_override("typing")
            self.parent_pet.set_state("idle")
            
        self.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
        
        if self.display_history and self.display_history[-1][0] == "model":
            self.display_history[-1] = ("model", response_text)
        else:
            self.display_history.append(("model", response_text))
            
        self.streaming_buffer = ""
        self.is_streaming = False
        self.geometry_locked = False
        self.rebuild_display()
        
        # After streaming finishes, perform exactly one geometry update
        if self.parent_pet:
            self.parent_pet.reposition_chat_window()

    def on_worker_error(self, error_message):
        self.message_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.message_input.setFocus()
        
        self.streaming_timer.stop()
        self.streaming_buffer = ""
        self.is_streaming = False
        self.geometry_locked = False
        
        if self.parent_pet:
            self.parent_pet.is_thinking = False
            from events.behavior_engine import scheduler_instance
            scheduler_instance.release_override("typing")
            self.parent_pet.set_state("idle")
            
        if self.chat_history and self.chat_history[-1]["role"] == "user":
            self.chat_history.pop()
            
        if self.display_history and self.display_history[-1][0] == "model":
            self.display_history.pop()
            
        self.append_message("model", error_message)
        
        if self.parent_pet:
            self.parent_pet.reposition_chat_window()

    def append_message(self, role, text):
        self.display_history.append((role, text))
        self.request_ui_refresh()

    def show_system_message(self, text):
        self.display_history.append(("system", text))
        self.request_ui_refresh()

    def toggle_dev_panel(self):
        """Toggles the visibility of the diagnostics drawer."""
        if self.dev_panel.isHidden():
            self.dev_panel.show()
            self.setFixedSize(606, 420)  # Expand size
        else:
            self.dev_panel.hide()
            self.setFixedSize(320, 420)  # Contract size
        self.update_state_view()

    def keyPressEvent(self, event):
        # Listen to Cmd + Shift + D or Ctrl + Shift + D
        is_d = (event.key() == Qt.Key_D)
        is_shift = bool(event.modifiers() & Qt.ShiftModifier)
        is_ctrl_or_cmd = bool(event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier))
        
        if is_d and is_shift and is_ctrl_or_cmd:
            self.toggle_dev_panel()
            event.accept()
        else:
            super().keyPressEvent(event)

    def on_routing_completed(self, data):
        self.last_telemetry = data
        self.update_state_view()

    def update_state_view(self):
        """Builds and prints the HTML debug tree inside the developer drawer."""
        # 1. Load active Mochi state
        state_html = f"""
        <font color="#fda4af"><b>=== MOCHI STATE ===</b></font><br/>
        <b>Mood:</b> {state_manager.mood}<br/>
        <b>Emotion:</b> {state_manager.emotion or 'None'}<br/>
        <b>Affection:</b> {state_manager.affection_level}<br/>
        <b>Energy:</b> {state_manager.energy}%<br/>
        <b>Focus Mode:</b> {'ON (Auto)' if state_manager.focus_mode else 'OFF'}<br/>
        <b>Idle:</b> {state_manager.idle_seconds}s (Typing: {state_manager.is_typing})<br/>
        <b>Messages (Session):</b> {state_manager.active_session_messages}<br/>
        <br/>
        """
        
        # 2. Last Route Trace diagnostics
        route_html = ""
        timeline_html = ""
        if self.last_telemetry:
            t = self.last_telemetry
            route_html = f"""
            <font color="#fda4af"><b>=== LAST ROUTE INFO ===</b></font><br/>
            <b>Query:</b> {t.get('query')}<br/>
            <b>Normalized:</b> {t.get('normalized')}<br/>
            <b>Intent:</b> {t.get('intent')}<br/>
            <b>Capability:</b> {t.get('capability')}<br/>
            <b>Cache Hit:</b> {'Yes' if t.get('cache_hit') else 'No'}<br/>
            <b>LLM Fallback:</b> {'Yes' if t.get('llm_called') else 'No'}<br/>
            <b>Overhead:</b> {t.get('router_overhead'):.2f}ms<br/>
            <b>Execution:</b> {t.get('execution_latency'):.2f}ms<br/>
            <b>Total:</b> {t.get('total_latency'):.2f}ms<br/>
            <br/>
            """
            timeline_html = "<font color='#fda4af'><b>=== ROUTE TIMELINE ===</b></font><br/>"
            for timestamp, step in t.get("timeline", []):
                time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                timeline_html += f"[{time_str}] {step}<br/>"
            timeline_html += "<br/>"
        else:
            route_html = "<font color='#fda4af'><b>=== LAST ROUTE INFO ===</b></font><br/>No queries processed yet.<br/><br/>"
            
        # 3. Aggregate statistics
        from services import analytics_service
        stats = analytics_service.get_aggregate_stats()
        stats_html = f"""
        <font color="#fda4af"><b>=== USAGE STATISTICS ===</b></font><br/>
        <b>Total Interactions:</b> {stats['total_interactions']}<br/>
        <b>Local Hit Rate:</b> {stats['local_hits_percentage']:.1f}%<br/>
        <b>LLM Fallback Rate:</b> {stats['llm_fallback_percentage']:.1f}%<br/>
        <b>Cache Hit Rate:</b> {stats['cache_hits_percentage']:.1f}%<br/>
        <b>Avg Latency:</b> {stats['avg_latency']:.1f}ms<br/>
        """
        if stats["top_capabilities"]:
            stats_html += "<b>Top Capabilities:</b><br/>"
            for tc in stats["top_capabilities"]:
                stats_html += f"&nbsp;&nbsp;• {tc['capability']}: {tc['count']}<br/>"
                
        # 4. Rendering statistics
        from events.event_bus import get_dropped_events_count
        rendering_html = f"""
        <font color="#fda4af"><b>=== RENDERING STATISTICS ===</b></font><br/>
        <b>Refresh Requests:</b> {self.metrics_refresh_requests}<br/>
        <b>Actual Repaints:</b> {self.metrics_actual_repaints}<br/>
        <b>Pending UI Refreshes:</b> {1 if self.refresh_pending else 0}<br/>
        <b>Streaming Buffer Size:</b> {len(self.streaming_buffer)} chars<br/>
        <b>Dropped Duplicate Events:</b> {get_dropped_events_count()}<br/>
        <b>Avg Rebuild Time:</b> {self.metrics_avg_rebuild_time:.2f}ms<br/>
        """
                
        html = f"""
        <html>
        <body style="font-family: monospace; color: #d4d4d4; font-size: 10px; line-height: 1.2;">
            {state_html}
            {route_html}
            {timeline_html}
            {stats_html}
            {rendering_html}
        </body>
        </html>
        """
        self.dev_display.setHtml(html)

    def rebuild_display(self):
        if self._updating_ui:
            return
        self._updating_ui = True
        
        import time
        start_time = time.perf_counter()
        
        try:
            self.chat_display.clear()
            html = ""
            for role, text in self.display_history:
                escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped_text)
                escaped_text = re.sub(r'^\*\s+', r'• ', escaped_text, flags=re.MULTILINE)
                formatted_text = escaped_text.replace("\n", "<br/>")
                
                if role == "user":
                    html += f"""
                        <div style="margin: 8px 0; text-align: right;">
                            <span style="background-color: #ffe4e6; color: #9f1239; border: 1px solid #fecdd3; border-radius: 12px 12px 2px 12px; padding: 8px 12px; display: inline-block; max-width: 80%; text-align: left; font-family: sans-serif;">
                                <b>You</b><br/>{formatted_text}
                            </span>
                        </div>
                    """
                elif role == "model":
                    html += f"""
                        <div style="margin: 8px 0; text-align: left;">
                            <span style="background-color: #ffffff; color: #4c0519; border: 1px solid #ffe4e6; border-radius: 12px 12px 12px 2px; padding: 8px 12px; display: inline-block; max-width: 80%; font-family: sans-serif;">
                                <b>🐾 Mochi</b><br/>{formatted_text}
                            </span>
                        </div>
                    """
                else: # system
                    html += f"""
                        <div style="margin: 8px 0; text-align: center;">
                            <span style="color: #fda4af; font-size: 11px; font-style: italic; font-family: sans-serif;">
                                {formatted_text}
                            </span>
                        </div>
                    """
            self.chat_display.setHtml(html)
            self.metrics_actual_repaints += 1
            
            # Smart Auto-Scroll to bottom: only if user is already near bottom (within 30px)
            scrollbar = self.chat_display.verticalScrollBar()
            is_near_bottom = (scrollbar.maximum() - scrollbar.value() <= 30) or (scrollbar.value() == 0)
            if is_near_bottom:
                QTimer.singleShot(10, lambda: scrollbar.setValue(scrollbar.maximum()))
                
        finally:
            self._updating_ui = False
            
        elapsed = (time.perf_counter() - start_time) * 1000.0
        self.metrics_avg_rebuild_time = 0.9 * self.metrics_avg_rebuild_time + 0.1 * elapsed
        
        # Real-time refresh for stats panel if expanded
        if not self.dev_panel.isHidden():
            self.update_state_view()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()


class DesktopPet(QWidget):
    def __init__(self, assets):
        super().__init__()
        self.assets = assets
        
        # Configure frameless, transparent window
        self.setWindowFlags(
            Qt.Window |                    
            Qt.FramelessWindowHint |       
            Qt.WindowStaysOnTopHint        
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)                     
        
        # Set fixed size of 128x128
        self.resize(128, 128)
        
        # State Machine setup
        # States: "IDLE", "SLEEPING", "TYPING"
        self.state = "IDLE"
        self.facing_right = True
        self.frame_index = 0
        self.current_frame = None
        
        # Idle tracking
        self.idle_seconds = 0
        self.is_thinking = False
        
        # Chat assistant window
        self.chat_window = None
        
        # Set up timers
        # 1. Animation loop (controls frame changes)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(120)  # Default ~8 FPS animation cycle
        
        # 2. Physics loop (keeps locked at bottom-right)
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.start(30)  
        
        # 3. Behavior loop (checks inactivity every second)
        self.behavior_timer = QTimer(self)
        self.behavior_timer.timeout.connect(self.update_behavior)
        self.behavior_timer.start(1000)  
        
        # 4. Typing Debounce Timer
        self.typing_debounce_timer = QTimer(self)
        self.typing_debounce_timer.setSingleShot(True)
        self.typing_debounce_timer.timeout.connect(self.on_typing_finished)
        
        # Global input listener integration
        self.input_listener = GlobalInputListener()
        self.input_listener.activity_detected.connect(self.on_global_activity)
        self.input_listener.keypress_detected.connect(self.on_global_typing)
        self.input_listener.start()
        
        # Connect to Notification Manager signals
        notification_manager.notification_triggered.connect(self.on_notification_received)
        
        # Subscribe to behavior events
        event_bus.subscribe("BEHAVIOR_CHANGED", self._on_behavior_changed)
        
        # Instantiate attention tracker
        from events.attention_tracker import tracker_instance
        tracker_instance.get_pet_geometry = self.geometry
        tracker_instance.get_pet_facing = lambda: self.facing_right
        self.tracker = tracker_instance
        self.tracker.start()
        
        # Initialize position and animation
        self.init_position()
        self.update_animation()

    def get_screen_geometry(self):
        screen = self.screen()
        if screen is not None:
            return screen.availableGeometry()
        return QApplication.primaryScreen().availableGeometry()

    def init_position(self):
        screen_geom = self.get_screen_geometry()
        x = screen_geom.right() - 138  # 128px size + 10px margin
        y = screen_geom.bottom() - 138 # 128px size + 10px margin
        self.setGeometry(x, y, 128, 128)
        log_debug(f"Position initialized bottom-right: x={x}, y={y}")

    def set_state(self, new_state):
        if self.state == new_state:
            return
            
        old_state = self.state
        self.state = new_state
        self.frame_index = 0
        
        # Resolve frame duration dynamic mapping via animation.json metadata if present
        meta = self.assets.get_animation_metadata(new_state)
        fps = meta.get("fps", 8)
        self.anim_timer.setInterval(int(1000 / fps))
        
        # Check sound events
        sound = meta.get("sound")
        if sound:
            event_bus.publish("PLAY_SOUND", name=sound)
            
        log_debug(f"State changed: {old_state} -> {self.state}")
        self.update_animation()

    def get_current_animation_list(self):
        return self.assets.get_animation_frames(self.state, self.facing_right)

    def update_animation(self):
        anim_list = self.get_current_animation_list()
        if not anim_list or len(anim_list) == 0:
            return
            
        self.frame_index = (self.frame_index + 1) % len(anim_list)
        self.current_frame = anim_list[self.frame_index]
        self.update()

    def update_physics(self):
        # Keep locked to bottom right corner
        screen_geom = self.get_screen_geometry()
        x = screen_geom.right() - 138
        y = screen_geom.bottom() - 138
        if self.x() != x or self.y() != y:
            self.move(x, y)

    def reposition_chat_window(self):
        if self.chat_window and self.chat_window.isVisible():
            if self.chat_window.geometry_locked:
                return  # Skip if chat geometry is locked during streaming
                
            chat_w = self.chat_window.width()
            chat_h = self.chat_window.height()
            target_x = self.x() - chat_w - 10
            target_y = (self.y() + 128) - chat_h
            
            # Boundary checks
            screen_geom = self.get_screen_geometry()
            if target_x < screen_geom.left():
                target_x = screen_geom.left() + 10
            if target_y < screen_geom.top():
                target_y = screen_geom.top() + 10
                
            # Only reposition if distance > 2 pixels
            current_pos = self.chat_window.pos()
            import math
            distance = math.hypot(target_x - current_pos.x(), target_y - current_pos.y())
            if distance > 2:
                self.chat_window.move(target_x, target_y)

    def moveEvent(self, event):
        super().moveEvent(event)
        self.reposition_chat_window()

    def update_behavior(self):
        # Alternate animations while thinking
        if self.is_thinking:
            self.thinking_ticks = getattr(self, "thinking_ticks", 0) + 1
            # Alternate: 3 seconds typing, 2 seconds idle
            cycle = self.thinking_ticks % 5
            if cycle < 3:
                if self.state != "typing":
                    self.set_state("typing")
            else:
                if self.state != "idle":
                    self.set_state("idle")
            self.idle_seconds = 0
            return
            
        self.thinking_ticks = 0
        
        # Idle timer check
        self.idle_seconds += 1
        
        # Update StateManager idle tracking so scheduler can query it
        state_manager.idle_seconds = self.idle_seconds
        
        # 1. Check for due reminders from the Scheduler
        scheduler.check_pending_reminders()
        
        # 2. Behavior engine tick (every 1s)
        is_active = (self.idle_seconds <= 1)
        proactive_msg = behavior_tick(self.idle_seconds, is_active)
        if proactive_msg and not state_manager.focus_mode:
            self.on_notification_received("🐾 Mochi Alert", proactive_msg)
            
        # Deadband Hysteresis Facing (only active when pet is idle)
        if self.idle_seconds > 2 and not self.is_thinking and not state_manager.is_typing:
            cursor_pos = self.tracker.get_cursor_position()
            pet_center_x = self.x() + self.width() // 2
            
            # Use hysteresis threshold of 30px
            if cursor_pos[0] < pet_center_x - 30:
                self.facing_right = False
            elif cursor_pos[0] > pet_center_x + 30:
                self.facing_right = True

    def on_notification_received(self, title, message):
        if self.chat_window is None:
            self.chat_window = AIAssistantChat(parent_pet=self)
            
        if not self.chat_window.isVisible():
            chat_w = self.chat_window.width()
            chat_h = self.chat_window.height()
            px = self.x() - chat_w - 10
            py = (self.y() + 128) - chat_h
            screen_geom = self.get_screen_geometry()
            if px < screen_geom.left():
                px = screen_geom.left() + 10
            if py < screen_geom.top():
                py = screen_geom.top() + 10
            self.chat_window.move(px, py)
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
            
        self.chat_window.append_message("model", message)

    def toggle_chat_window(self):
        if self.chat_window is None:
            self.chat_window = AIAssistantChat(parent_pet=self)
            
        if self.chat_window.isVisible():
            self.chat_window.hide()
        else:
            # Position to the left of the pet
            chat_w = self.chat_window.width()
            chat_h = self.chat_window.height()
            
            px = self.x() - chat_w - 10
            py = (self.y() + 128) - chat_h
            
            # Boundary checks
            screen_geom = self.get_screen_geometry()
            if px < screen_geom.left():
                px = screen_geom.left() + 10
            if py < screen_geom.top():
                py = screen_geom.top() + 10
                
            self.chat_window.move(px, py)
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()

    def _on_behavior_changed(self, name, duration):
        if self.is_thinking:
            return
        if state_manager.is_typing:
            return
        self.set_state(name)

    def on_global_activity(self):
        self.idle_seconds = 0
        state_manager.idle_seconds = 0
        if self.state == "sleep" or self.state == "SLEEPING":
            self.set_state("idle")

    def on_global_typing(self):
        if self.is_thinking:
            return  # Skip manual keyboard events if pet is currently in thinking animation
            
        self.idle_seconds = 0
        if self.state == "sleep" or self.state == "SLEEPING":
            self.set_state("idle")
            
        # Typing decrements Mochi's cursor interest levels
        if hasattr(self, "tracker"):
            self.tracker.change_interest(-2.0)
        
        # Skip typing animation if chat box input field has focus
        if self.chat_window and self.chat_window.message_input.hasFocus():
            return
            
        # Debounced typing state transition
        if not state_manager.is_typing:
            state_manager.is_typing = True
            from events.behavior_engine import scheduler_instance, HIGH
            scheduler_instance.request_override("typing", HIGH)
            
        # Restart debounce timer
        self.typing_debounce_timer.start(2000)

    def on_typing_finished(self):
        """Called when user has not typed for 2 seconds."""
        if self.is_thinking:
            return
        state_manager.is_typing = False
        from events.behavior_engine import scheduler_instance
        scheduler_instance.release_override("typing")

    def show_preview_dialog(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QLabel, QPushButton
        dialog = QDialog(self)
        dialog.setWindowTitle("🐾 Animation Preview")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #202020;
                color: #e0e0e0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel {
                color: #fda4af;
                font-size: 13px;
                font-weight: bold;
            }
            QListWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        layout = QVBoxLayout(dialog)
        label = QLabel("Select variant to preview:", dialog)
        layout.addWidget(label)
        
        list_widget = QListWidget(dialog)
        variants = [
            "idle", "look_left", "look_right", "tail_flick", "stretch", "groom", "yawn", "sit", "sleep", "wake",
            "[Simulate Cursor Near]", "[Simulate Cursor Fast]", "[Simulate Cursor Idle]", "[Simulate Hover]"
        ]
        list_widget.addItems(variants)
        layout.addWidget(list_widget)
        
        btn = QPushButton("Play Selection / Simulate", dialog)
        layout.addWidget(btn)
        
        def play_selected():
            item = list_widget.currentItem()
            if item:
                chosen = item.text()
                from events.behavior_engine import scheduler_instance, HIGH, NORMAL
                from events import event_bus
                
                if chosen == "[Simulate Cursor Near]":
                    pet_center = self.tracker.get_pet_center()
                    self.tracker.current_pos = (pet_center[0] - 100, pet_center[1])
                    self.tracker.is_near = True
                    self.tracker.time_in_zone = 5.0
                    event_bus.publish("CURSOR_NEAR")
                elif chosen == "[Simulate Cursor Fast]":
                    self.tracker.velocity = 1500.0
                    event_bus.publish("CURSOR_FAST")
                elif chosen == "[Simulate Cursor Idle]":
                    self.tracker.velocity = 0.0
                    event_bus.publish("CURSOR_IDLE")
                elif chosen == "[Simulate Hover]":
                    pet_center = self.tracker.get_pet_center()
                    self.tracker.current_pos = (pet_center[0] - 10, pet_center[1] - 10)
                    self.tracker.is_near = True
                    self.tracker.is_hovering = True
                    event_bus.publish("CURSOR_HOVERING")
                else:
                    scheduler_instance.request_override(chosen, HIGH, duration=4.0)
                dialog.accept()
                
        list_widget.itemDoubleClicked.connect(play_selected)
        btn.clicked.connect(play_selected)
        
        dialog.setLayout(layout)
        dialog.resize(260, 340)
        dialog.exec_()

    # Click triggers
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Pet interaction increases cursor interest levels
            if hasattr(self, "tracker"):
                self.tracker.change_interest(20.0)
                
            if self.state == "sleep" or self.state == "SLEEPING":
                self.set_state("idle")
                self.idle_seconds = 0
                event.accept()
                return
                
            self.toggle_chat_window()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.current_frame and not self.current_frame.isNull():
            painter.drawPixmap(0, 0, self.current_frame)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #202020;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 16px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
        """)
        
        # Focus Mode Action
        focus_action = menu.addAction("Focus Mode")
        focus_action.setCheckable(True)
        focus_action.setChecked(state_manager.focus_mode)
        
        # Preview Animations Action
        preview_action = menu.addAction("Preview Animations...")
        
        exit_action = menu.addAction("Exit Pet")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        if action == focus_action:
            state_manager.focus_mode = focus_action.isChecked()
            log_info(f"Focus Mode manually set to: {state_manager.focus_mode}")
        elif action == preview_action:
            self.show_preview_dialog()
        elif action == exit_action:
            QApplication.quit()

    def closeEvent(self, event):
        # Save episodic memory summary of the active conversation on close
        if self.chat_window and self.chat_window.chat_history:
            mapped_history = []
            for msg in self.chat_window.chat_history:
                role = msg.get("role")
                parts = msg.get("parts", [])
                text = parts[0].get("text", "") if parts else ""
                mapped_history.append({"role": role, "text": text})
            try:
                from memory import episodic_memory
                episodic_memory.save_session_summary(mapped_history)
            except Exception as e:
                log_error(f"Error saving session summary on close: {e}")

        if self.chat_window:
            self.chat_window.close()
        if hasattr(self, 'input_listener'):
            self.input_listener.stop()
        super().closeEvent(event)
