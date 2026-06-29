import unittest
import time
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication, QTextBrowser, QScrollBar
from PyQt5.QtCore import QPoint, QRect, QEventLoop, QTimer

# Initialize QApplication once for PyQt tests
app = QApplication.instance()
if not app:
    app = QApplication([])

from events import event_bus
from events.behavior_engine import scheduler_instance
from pet import DesktopPet, AIAssistantChat

class TestUIStability(unittest.TestCase):
    def setUp(self):
        # Reset EventBus registry
        event_bus._subscribers.clear()
        event_bus._dropped_events_count = 0
        
        # Reset behavior scheduler
        scheduler_instance.last_published_state = None
        scheduler_instance.override_state = None
        scheduler_instance.override_priority = None

    def test_event_bus_duplicate_subscription_guard(self):
        callback_called = 0
        def test_callback():
            nonlocal callback_called
            callback_called += 1
            
        # Subscribe twice
        event_bus.subscribe("TEST_EVENT", test_callback)
        event_bus.subscribe("TEST_EVENT", test_callback)
        
        # Publish
        event_bus.publish("TEST_EVENT")
        
        # Assert callback called exactly once, and duplicate dropped metric updated
        self.assertEqual(callback_called, 1)
        self.assertEqual(event_bus.get_dropped_events_count(), 1)

    def test_state_change_debounce(self):
        published_states = []
        def on_behavior(name, duration):
            published_states.append(name)
            
        event_bus.subscribe("BEHAVIOR_CHANGED", on_behavior)
        
        # Trigger overrides of same state multiple times
        scheduler_instance.request_override("sleeping", 3, duration=5.0)
        scheduler_instance.request_override("sleeping", 3, duration=5.0)
        scheduler_instance.request_override("sleeping", 3, duration=5.0)
        
        # Verify event was broadcasted only once
        self.assertEqual(published_states, ["sleeping"])

    def test_stable_follow_hysteresis_and_lock(self):
        # Instantiate a mock pet and chat window
        mock_assets = MagicMock()
        pet = DesktopPet(mock_assets)
        chat = AIAssistantChat(parent_pet=pet)
        pet.chat_window = chat
        
        # Initial positions (far enough from screen edges to avoid boundary clamping)
        pet.move(800, 500)
        chat.setVisible(True)
        chat.geometry_locked = False
        
        # Snap the chat window to the correct target using Mochi's own layout rules
        pet.reposition_chat_window()
        snap_pos = chat.pos()
        
        # Move pet by 1 pixel (distance < 2px threshold)
        pet.move(801, 500)
        # Chat window should NOT move
        self.assertEqual(chat.pos(), snap_pos)
        
        # Move pet by 10 pixels (distance > 2px threshold)
        pet.move(810, 500)
        # Chat window SHOULD move
        expected_x = pet.x() - chat.width() - 10
        expected_y = (pet.y() + 128) - chat.height()
        # Verify it moved near expected position
        self.assertTrue(abs(chat.x() - expected_x) < 50)
        
        # Lock geometry and move pet again by 20 pixels
        chat.geometry_locked = True
        last_pos = chat.pos()
        pet.move(830, 500)
        pet.reposition_chat_window()
        # Chat window should NOT move because geometry is locked during streaming
        self.assertEqual(chat.pos(), last_pos)
        
        chat.close()
        pet.close()

    def test_smart_auto_scroll(self):
        mock_assets = MagicMock()
        chat = AIAssistantChat(parent_pet=None)
        
        # Mock scrollbar value & maximum
        scrollbar = chat.chat_display.verticalScrollBar()
        scrollbar.maximum = MagicMock(return_value=100)
        scrollbar.setValue = MagicMock()
        
        # Case 1: Scrollbar value is far from bottom (e.g. 50, maximum is 100, delta = 50 > 30)
        scrollbar.value = MagicMock(return_value=50)
        chat.display_history.append(("model", "New text"))
        chat.rebuild_display()
        # Should NOT scroll to bottom
        scrollbar.setValue.assert_not_called()
        
        # Case 2: Scrollbar value is near bottom (e.g. 85, maximum is 100, delta = 15 <= 30)
        scrollbar.value = MagicMock(return_value=85)
        chat.display_history.append(("model", "More text"))
        chat.rebuild_display()
        
        # Let QTimer single shots run
        loop = QEventLoop()
        QTimer.singleShot(25, loop.quit)
        loop.exec_()
        
        # Should setValue to maximum
        scrollbar.setValue.assert_called_with(100)
        
        chat.close()

    def test_streaming_stress_test(self):
        # 1000-token streaming stress test
        chat = AIAssistantChat(parent_pet=None)
        chat.display_history.clear()
        
        # Verify initial repaint metric
        initial_repaints = chat.metrics_actual_repaints
        
        # Emulate receiving 1000 tokens sequentially
        # Tokens arrive fast (no delay so they queue up in the buffer)
        for i in range(1000):
            chat.on_token_received(f" tok{i}")
            
        # Verify all tokens accumulated in the streaming buffer
        self.assertEqual(len(chat.streaming_buffer.split()), 1000)
        self.assertTrue(chat.is_streaming)
        self.assertTrue(chat.geometry_locked)
        
        # Allow QTimer event loops to run and process the streaming refresh ticks
        loop = QEventLoop()
        # Fast-forward timer by executing a short event loop
        # The 100ms streaming_timer will fire and flush the buffer
        QTimer.singleShot(150, loop.quit)
        loop.exec_()
        
        # Verify the tokens have been flushed from streaming buffer to display history
        self.assertEqual(len(chat.streaming_buffer), 0)
        self.assertEqual(len(chat.display_history), 1)  # Exactly one model message block
        
        role, text = chat.display_history[-1]
        self.assertEqual(role, "model")
        self.assertTrue("tok0" in text)
        self.assertTrue("tok999" in text)
        
        # Finish the stream
        expected_final_text = text
        chat.on_worker_finished(expected_final_text)
        
        # Verify geometry unlocked
        self.assertFalse(chat.is_streaming)
        self.assertFalse(chat.geometry_locked)
        
        # Rebuild count should be extremely small compared to 1000 tokens (coalesced via 100ms/50ms queue)
        total_repaints_made = chat.metrics_actual_repaints - initial_repaints
        self.assertTrue(total_repaints_made < 10)  # Throttled down to only 1-2 repaints during the 150ms run!
        
        chat.close()
