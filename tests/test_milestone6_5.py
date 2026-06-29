import unittest
import os
import json
import time
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication
from config import settings

# Redirect database path to a test database
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_milestone6_5_test.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from events import event_bus
from events.attention_tracker import AttentionTracker
from events.behavior_engine import scheduler_instance, LOW, NORMAL, HIGH, CRITICAL, BehaviorScheduler
from assistant.state.state_manager import state_manager
from assets import PetAssets

class TestMilestone65(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q_app = QApplication.instance() or QApplication([])
        db_manager.init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def setUp(self):
        state_manager.mood = "Relaxed"
        state_manager.energy = 80
        state_manager.idle_seconds = 0
        state_manager.focus_mode = False
        
        # Reset behavior scheduler
        scheduler_instance.current_behavior = scheduler_instance.behaviors["relaxing"]
        scheduler_instance.current_animation = scheduler_instance.current_behavior.animations[0]
        scheduler_instance.current_variant = scheduler_instance.current_animation.variants[0]
        scheduler_instance.current_variant.interruptible = True
        scheduler_instance.override_state = None
        scheduler_instance.override_priority = None
        scheduler_instance.override_duration = None
        scheduler_instance.pause_time_left = 0.0
        scheduler_instance.time_left = 5.0
        scheduler_instance.history.clear()
        scheduler_instance.blacklist.clear()
        
    def test_elliptical_zone_math(self):
        # Set up a tracker with fixed pet geometries: pet centered at (500, 500)
        tracker = AttentionTracker(
            get_pet_geometry_cb=lambda: QRect(436, 436, 128, 128),  # Center: (500, 500)
            get_pet_facing_cb=lambda: True
        )
        
        # 1. Position inside: (450, 500) -> dx=-50, dy=0
        # Inside ellipse (220, 160)
        tracker.current_pos = (450, 500)
        self.assertTrue(tracker.check_proximity_ellipse(220, 160))
        
        # 2. Position outside horizontally: (800, 500) -> dx=300, dy=0
        tracker.current_pos = (800, 500)
        self.assertFalse(tracker.check_proximity_ellipse(220, 160))
        
        # 3. Position outside vertically: (500, 700) -> dx=0, dy=200
        tracker.current_pos = (500, 700)
        self.assertFalse(tracker.check_proximity_ellipse(220, 160))
        
        tracker.stop()

    def test_attention_zones_facing(self):
        # Center at (500, 500)
        tracker = AttentionTracker(
            get_pet_geometry_cb=lambda: QRect(436, 436, 128, 128),
            get_pet_facing_cb=lambda: True  # Facing right
        )
        
        # 1. Facing Right, cursor right: (600, 500) -> dx=100 -> front
        tracker.current_pos = (600, 500)
        self.assertEqual(tracker.get_direction(), "front")
        
        # 2. Facing Right, cursor left: (400, 500) -> dx=-100 -> behind
        tracker.current_pos = (400, 500)
        self.assertEqual(tracker.get_direction(), "behind")
        
        # 3. Facing Right, cursor above: (500, 400) -> dy=-100 -> above
        tracker.current_pos = (500, 400)
        self.assertEqual(tracker.get_direction(), "above")
        
        # 4. Flip facing direction to Left
        tracker.get_pet_facing = lambda: False  # Facing left
        
        # Facing Left, cursor left: (400, 500) -> dx=-100 -> front
        tracker.current_pos = (400, 500)
        self.assertEqual(tracker.get_direction(), "front")
        
        # Facing Left, cursor right: (600, 500) -> dx=100 -> behind
        tracker.current_pos = (600, 500)
        self.assertEqual(tracker.get_direction(), "behind")
        
        tracker.stop()

    def test_adaptive_polling_and_confidence(self):
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QCursor
        from unittest.mock import MagicMock
        
        # Save original QCursor.pos method
        original_pos_method = QCursor.pos
        
        try:
            # Mock screen cursor position to far static coordinates
            QCursor.pos = MagicMock(return_value=QPoint(800, 800))
            
            tracker = AttentionTracker(
                get_pet_geometry_cb=lambda: QRect(436, 436, 128, 128),
                get_pet_facing_cb=lambda: True
            )
            
            tracker.poll()
            tracker.poll()  # Second poll, now velocity is guaranteed 0
            
            # Far & static -> interval should adapt to 250ms
            self.assertEqual(tracker.current_interval, 250)
            
            # Mock hover position (static coordinates near pet center)
            QCursor.pos = MagicMock(return_value=QPoint(505, 505))
            tracker.poll()
            tracker.poll()
            # Hovering -> interval should adapt to 50ms
            self.assertEqual(tracker.current_interval, 50)
            
            # Test confidence delay: lingers in zone
            tracker.is_near = False
            tracker.confidence_accumulated = 0.1
            tracker.poll()
            self.assertFalse(tracker.is_near)  # Not near yet (accumulated < 0.3s)
            
            tracker.confidence_accumulated = 0.4
            tracker.poll()
            self.assertTrue(tracker.is_near)  # Is near now (accumulated >= 0.3s)
            
            tracker.stop()
        finally:
            # Restore original method
            QCursor.pos = original_pos_method

    def test_interest_and_bored_progression(self):
        tracker = AttentionTracker(
            get_pet_geometry_cb=lambda: QRect(436, 436, 128, 128),
            get_pet_facing_cb=lambda: True
        )
        
        # Initialize
        tracker.interest = 50.0
        tracker.change_interest(20)
        self.assertEqual(tracker.interest, 70.0)
        
        tracker.change_interest(-100)
        self.assertEqual(tracker.interest, 0.0)  # Lower bound check
        
        # Test bored state progression in behavior scheduler (targets tracker_instance directly)
        from events.attention_tracker import tracker_instance
        old_near = tracker_instance.is_near
        old_t = tracker_instance.time_in_zone
        
        tracker_instance.is_near = True
        tracker_instance.time_in_zone = 25.0  # Lingered for > 20s
        
        # Re-evaluate behavior weights
        scheduler_instance.time_left = 0.0
        scheduler_instance.pause_time_left = 0.0
        variant = scheduler_instance.tick_scheduler(is_idle=True)
        
        # Restore old values
        tracker_instance.is_near = old_near
        tracker_instance.time_in_zone = old_t
        
        # When bored, only 'ignoring' or 'yawn' (inside relaxing) are valid
        self.assertIn(scheduler_instance.current_behavior.name, ["ignoring", "relaxing"])
        
        tracker.stop()

    def test_interaction_overrides(self):
        fast_triggered = False
        def on_fast():
            nonlocal fast_triggered
            fast_triggered = True
            
        event_bus.subscribe("CURSOR_FAST", on_fast)
        
        # Simulate fast mouse movement near Mochi
        event_bus.publish("CURSOR_FAST")
        self.assertTrue(fast_triggered)
        
        # Verify startled override was requested
        self.assertEqual(scheduler_instance.override_state, "surprised")
        self.assertEqual(scheduler_instance.override_priority, NORMAL)

    def test_asset_fallback_chain(self):
        assets = PetAssets()
        
        # 1. paw_swipe -> tail_flick -> idle
        frames = assets.get_animation_frames("paw_swipe")
        self.assertEqual(len(frames), len(assets.idle_right))
        
        # 2. surprised -> look_around -> idle
        frames_surprised = assets.get_animation_frames("surprised")
        self.assertEqual(len(frames_surprised), len(assets.idle_right))

if __name__ == '__main__':
    unittest.main()
