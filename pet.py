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
            self.parent_pet.set_state("TYPING")
            
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

    def on_token_received(self, token):
        if not self.is_streaming:
            self.is_streaming = True
            self.display_history.append(("model", ""))
            
        role, text = self.display_history[-1]
        self.display_history[-1] = (role, text + token)
        self.rebuild_display()

    def on_worker_finished(self, response_text):
        self.message_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.message_input.setFocus()
        
        if self.parent_pet:
            self.parent_pet.is_thinking = False
            self.parent_pet.set_state("IDLE")
            
        self.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
        
        if not self.is_streaming:
            self.append_message("model", response_text)
        else:
            self.display_history[-1] = ("model", response_text)
            self.rebuild_display()

    def on_worker_error(self, error_message):
        self.message_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.message_input.setFocus()
        
        if self.parent_pet:
            self.parent_pet.is_thinking = False
            self.parent_pet.set_state("IDLE")
            
        if self.chat_history and self.chat_history[-1]["role"] == "user":
            self.chat_history.pop()
            
        if hasattr(self, 'is_streaming') and self.is_streaming:
            self.display_history.pop()
            
        self.append_message("model", error_message)

    def append_message(self, role, text):
        self.display_history.append((role, text))
        self.rebuild_display()

    def show_system_message(self, text):
        self.display_history.append(("system", text))
        self.rebuild_display()

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
                
        html = f"""
        <html>
        <body style="font-family: monospace; color: #d4d4d4; font-size: 10px; line-height: 1.2;">
            {state_html}
            {route_html}
            {timeline_html}
            {stats_html}
        </body>
        </html>
        """
        self.dev_display.setHtml(html)

    def rebuild_display(self):
        self.chat_display.clear()
        html = ""
        for role, text in self.display_history:
            escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Simple markdown parsing
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
        QTimer.singleShot(10, lambda: self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum()))

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
        self.typing_cooldown = 0
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
        
        # Global input listener integration
        self.input_listener = GlobalInputListener()
        self.input_listener.activity_detected.connect(self.on_global_activity)
        self.input_listener.typing_detected.connect(self.on_global_typing)
        self.input_listener.start()
        
        # Connect to Notification Manager signals
        notification_manager.notification_triggered.connect(self.on_notification_received)
        
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
        print(f"[Debug] Position initialized bottom-right: x={x}, y={y}")

    def set_state(self, new_state):
        if self.state == new_state:
            return
            
        old_state = self.state
        self.state = new_state
        self.frame_index = 0
        
        profile = state_manager.get_animation_profile()
        self.anim_timer.setInterval(profile.interval)
            
        print(f"[Debug] State changed: {old_state} -> {self.state}")
        self.update_animation()

    def get_current_animation_list(self):
        if self.state == "SLEEPING":
            return self.assets.sleep_right if self.facing_right else self.assets.sleep_left
        elif self.state == "TYPING":
            return self.assets.typing_right if self.facing_right else self.assets.typing_left
        else:  # IDLE
            return self.assets.idle_right if self.facing_right else self.assets.idle_left

    def update_animation(self):
        anim_list = self.get_current_animation_list()
        if not anim_list:
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

    def update_behavior(self):
        if self.is_thinking:
            if self.state != "TYPING":
                self.set_state("TYPING")
            self.idle_seconds = 0
            return
            
        if self.state == "TYPING":
            self.typing_cooldown -= 1
            if self.typing_cooldown <= 0:
                self.set_state("IDLE")
        
        # Idle timer check
        self.idle_seconds += 1
        
        # 1. Check for due reminders from the Scheduler
        scheduler.check_pending_reminders()
        
        # 2. Behavior engine tick (every 1s)
        is_active = (self.idle_seconds <= 1)
        proactive_msg = behavior_tick(self.idle_seconds, is_active)
        if proactive_msg:
            self.on_notification_received("🐾 Mochi Alert", proactive_msg)
            
        # Get active profile and update speed
        profile = state_manager.get_animation_profile()
        self.anim_timer.setInterval(profile.interval)
            
        # 3. Micro idle behaviors: trigger micro animation state changes via profile probabilities
        if self.idle_seconds > 0 and self.idle_seconds % 20 == 0:
            if self.state == "IDLE":
                actions = list(profile.probabilities.keys())
                probs = list(profile.probabilities.values())
                chosen = random.choices(actions, weights=probs, k=1)[0]
                
                # Map selected behavior to visual state
                if chosen in ["yawn", "stretch", "sleep"]:
                    self.set_state("SLEEPING")
                    self.typing_cooldown = 4
                elif chosen in ["hop", "typing"]:
                    self.set_state("TYPING")
                    self.typing_cooldown = 3
                else:
                    self.set_state("IDLE")
                
        if self.idle_seconds >= 60:
            if self.state != "SLEEPING":
                self.set_state("SLEEPING")

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

    def on_global_activity(self):
        self.idle_seconds = 0
        if self.state == "SLEEPING":
            print("[Debug] Activity detected, waking pet.")
            self.set_state("IDLE")

    def on_global_typing(self):
        if self.is_thinking:
            return  # Skip manual keyboard events if pet is currently in thinking animation
            
        self.idle_seconds = 0
        if self.state == "SLEEPING":
            self.set_state("IDLE")
        
        # Skip typing animation if chat box input field has focus
        if self.chat_window and self.chat_window.message_input.hasFocus():
            return
            
        # Show typing animation briefly
        if self.state == "IDLE":
            self.set_state("TYPING")
            self.typing_cooldown = 2
        elif self.state == "TYPING":
            self.typing_cooldown = 2

    # Click triggers
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.state == "SLEEPING":
                self.set_state("IDLE")
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
        
        exit_action = menu.addAction("Exit Pet")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        if action == focus_action:
            state_manager.focus_mode = focus_action.isChecked()
            print(f"[Pet] Focus Mode manually set to: {state_manager.focus_mode}")
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
                print(f"[Pet] Error saving session summary on close: {e}")

        if self.chat_window:
            self.chat_window.close()
        if hasattr(self, 'input_listener'):
            self.input_listener.stop()
        super().closeEvent(event)
