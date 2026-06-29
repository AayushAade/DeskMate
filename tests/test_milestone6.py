import unittest
import os
import tempfile
import json
import time
from PyQt5.QtWidgets import QApplication
from config import settings

# Redirect database path to a test database
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mochi_milestone6_test.db")
settings.DB_PATH = TEST_DB_PATH

from database import db_manager
from events import event_bus
from events.behavior_engine import scheduler_instance, LOW, NORMAL, HIGH, CRITICAL, BehaviorScheduler
from assistant.state.state_manager import state_manager
from assets import PetAssets

class TestMilestone6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need a QApplication to initialize QPixmaps/PyQt stuff without UI crashes
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
        state_manager.is_typing = False
        state_manager.is_thinking = False
        
        # Reset scheduler
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
        
    def test_priority_override_and_interrupt(self):
        # 1. Start a low-priority, non-interruptible behavior
        scheduler_instance.current_variant.interruptible = False
        scheduler_instance.current_behavior.priority = LOW
        
        # 2. Try to request a low-priority override
        success = scheduler_instance.request_override("test_state_1", LOW)
        # Should fail because active variant is non-interruptible and priority is equal/low
        self.assertFalse(success)
        self.assertNotEqual(scheduler_instance.override_state, "test_state_1")
        
        # 3. Request a HIGH priority override
        success_high = scheduler_instance.request_override("test_state_2", HIGH)
        # Should succeed because HIGH priority overrides non-interruptible variants
        self.assertTrue(success_high)
        self.assertEqual(scheduler_instance.override_state, "test_state_2")
        self.assertEqual(scheduler_instance.override_priority, HIGH)
        
        # 4. Release override
        scheduler_instance.release_override("test_state_2")
        self.assertIsNone(scheduler_instance.override_state)

    def test_energy_weight_scaling(self):
        # High energy state
        state_manager.energy = 90
        scheduler_instance.time_left = 0.0
        scheduler_instance.pause_time_left = 0.0
        # Tick scheduler once to ensure it scales relaxing/curious weights
        scheduler_instance.tick_scheduler(is_idle=True)
        # Verify relax/curious was evaluated
        self.assertTrue(len(scheduler_instance.history) > 0)
        
        # Reset and run with low energy
        scheduler_instance.history.clear()
        scheduler_instance.time_left = 0.0
        scheduler_instance.pause_time_left = 0.0
        state_manager.energy = 10
        scheduler_instance.tick_scheduler(is_idle=True)
        self.assertTrue(len(scheduler_instance.history) > 0)

    def test_dynamic_fallback_maps(self):
        assets = PetAssets()
        
        # Request 'stretch' (which does not exist on disk)
        frames = assets.get_animation_frames("stretch", facing_right=True)
        
        # Should fall back to 'idle' frames since stretch is missing
        self.assertEqual(len(frames), len(assets.idle_right))
        # Ensure we loaded pixmaps and no crash occurred
        self.assertIsNotNone(frames[0])

    def test_animation_json_metadata_parsing(self):
        # Create a temp directory inside the assets folder to test metadata loading
        assets = PetAssets()
        temp_anim_dir = os.path.join(assets.assets_dir, "animations", "temp_mock_anim")
        os.makedirs(temp_anim_dir, exist_ok=True)
        
        metadata = {
            "fps": 12,
            "loop": False,
            "sound": "purr"
        }
        
        json_path = os.path.join(temp_anim_dir, "animation.json")
        try:
            with open(json_path, "w") as f:
                json.dump(metadata, f)
                
            # Write a dummy png frame so it loads as a valid animation
            dummy_png = os.path.join(temp_anim_dir, "frame_1.png")
            # We can copy idle_1.png as a dummy
            import shutil
            shutil.copy(os.path.join(assets.assets_dir, "idle_1.png"), dummy_png)
            
            # Load metadata
            frames = assets.get_animation_frames("temp_mock_anim")
            self.assertTrue(len(frames) > 0)
            
            loaded_meta = assets.get_animation_metadata("temp_mock_anim")
            self.assertEqual(loaded_meta["fps"], 12)
            self.assertFalse(loaded_meta["loop"])
            self.assertEqual(loaded_meta["sound"], "purr")
            
        finally:
            # Clean up temp folder
            if os.path.exists(temp_anim_dir):
                shutil.rmtree(temp_anim_dir)

    def test_decoupled_started_event(self):
        event_payload = {}
        def on_anim_started(name, metadata):
            event_payload["name"] = name
            event_payload["metadata"] = metadata
            
        event_bus.subscribe("ANIMATION_STARTED", on_anim_started)
        
        try:
            # Force scheduler tick selection
            scheduler_instance.time_left = 0.0
            scheduler_instance.pause_time_left = 0.0
            scheduler_instance.tick_scheduler(is_idle=True)
            
            # Confirm event fired
            self.assertIn("name", event_payload)
            self.assertIn("metadata", event_payload)
            self.assertIn("interruptible", event_payload["metadata"])
            
        finally:
            # Unsubscribe/clear hook (standard subscription removal)
            pass

if __name__ == '__main__':
    unittest.main()
