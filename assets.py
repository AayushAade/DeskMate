import os
import glob
import re
import json
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTransform, QPainter
from config.settings import log_info, log_error, log_debug

# Belief maps for missing assets
FALLBACK_MAP = {
    "paw_swipe": "tail_flick",
    "surprised": "look_around",
    "look_left": "look_around",
    "look_right": "look_around",
    "look_around": "idle",
    "tail_flick": "idle",
    "stretch": "idle",
    "groom": "sit",
    "yawn": "idle",
    "sit": "idle",
    "sleep": "sit",
    "wake": "idle"
}

class PetAssets:
    def __init__(self, assets_dir=None):
        if assets_dir is None:
            assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        
        self.assets_dir = assets_dir
        
        # Cache for loaded frames: (name, facing_right) -> list of QPixmaps
        self._animation_cache = {}
        # Cache for parsed metadata: name -> dict
        self._animation_metadata = {}
        
        # Lists to hold standard preloaded frames
        self.idle_right = []
        self.idle_left = []
        
        self.walk_right = []
        self.walk_left = []
        
        self.typing_right = []
        self.typing_left = []
        
        self.petted_right = []
        self.petted_left = []
        
        self.fall_right = []
        self.fall_left = []
        
        self.lie_right = []
        self.lie_left = []
        
        self.sleep_right = []
        self.sleep_left = []
        
        self.load_assets()

    def _load_and_verify(self, filename):
        path = os.path.join(self.assets_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Required asset not found: '{path}'.\n"
                f"Please ensure all required cropped PNG frames are placed inside the 'assets' folder."
            )
        pixmap = QPixmap(path)
        if pixmap.isNull():
            raise ValueError(f"Failed to load image file (file might be corrupted): '{path}'")
            
        scaled = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        canvas = QPixmap(128, 128)
        canvas.fill(Qt.transparent)
        
        painter = QPainter(canvas)
        x = (128 - scaled.width()) // 2
        y = (128 - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        
        return canvas

    def _mirror_frame(self, pixmap):
        transform = QTransform().scale(-1, 1)
        return pixmap.transformed(transform)

    def load_assets(self):
        # 1. Load Idle frames (idle_1.png to idle_4.png)
        for i in range(1, 5):
            filename = f"idle_{i}.png"
            pixmap = self._load_and_verify(filename)
            self.idle_right.append(pixmap)
            self.idle_left.append(self._mirror_frame(pixmap))
            
        # 2. Load Walk frames (walk_1.png to walk_6.png)
        for i in range(1, 7):
            filename = f"walk_{i}.png"
            pixmap = self._load_and_verify(filename)
            self.walk_right.append(pixmap)
            self.walk_left.append(self._mirror_frame(pixmap))
            
        # 3. Load Fall frame (fall.png)
        fall_pix = self._load_and_verify("fall.png")
        self.fall_right = [fall_pix]
        self.fall_left = [self._mirror_frame(fall_pix)]
        
        # 4. Load Lie frame (lie.png)
        lie_pix = self._load_and_verify("lie.png")
        self.lie_right = [lie_pix]
        self.lie_left = [self._mirror_frame(lie_pix)]
        
        # 5. Load Sleep frame (sleep.png)
        sleep_pix = self._load_and_verify("sleep.png")
        self.sleep_right = [sleep_pix]
        self.sleep_left = [self._mirror_frame(sleep_pix)]
        
        # 6. Load Typing frames (type_1.png to type_4.png)
        for i in range(1, 5):
            filename = f"type_{i}.png"
            pixmap = self._load_and_verify(filename)
            self.typing_right.append(pixmap)
            self.typing_left.append(self._mirror_frame(pixmap))
            
        # 7. Load Petting frames (pet_1.png to pet_4.png)
        for i in range(1, 5):
            filename = f"pet_{i}.png"
            pixmap = self._load_and_verify(filename)
            self.petted_right.append(pixmap)
            self.petted_left.append(self._mirror_frame(pixmap))

        # Seed initial cache with preloaded animations
        self._animation_cache[("idle", True)] = self.idle_right
        self._animation_cache[("idle", False)] = self.idle_left
        self._animation_cache[("walk", True)] = self.walk_right
        self._animation_cache[("walk", False)] = self.walk_left
        self._animation_cache[("typing", True)] = self.typing_right
        self._animation_cache[("typing", False)] = self.typing_left
        self._animation_cache[("petting", True)] = self.petted_right
        self._animation_cache[("petting", False)] = self.petted_left
        self._animation_cache[("fall", True)] = self.fall_right
        self._animation_cache[("fall", False)] = self.fall_left
        self._animation_cache[("lie", True)] = self.lie_right
        self._animation_cache[("lie", False)] = self.lie_left
        self._animation_cache[("sleep", True)] = self.sleep_right
        self._animation_cache[("sleep", False)] = self.sleep_left

        log_info("Preloaded standard assets successfully.")

    def _load_dynamic_animation(self, name: str) -> list:
        """Scans filesystem locations for directories or root files and loads QPixmaps."""
        frames = []
        
        # 1. Search candidates: assets/animations/{name}, assets/{name}
        search_dirs = [
            os.path.join(self.assets_dir, "animations", name),
            os.path.join(self.assets_dir, name)
        ]
        
        # Check subdirectories
        for sdir in search_dirs:
            if os.path.isdir(sdir):
                # Check for metadata animation.json
                meta_path = os.path.join(sdir, "animation.json")
                if os.path.isfile(meta_path):
                    try:
                        with open(meta_path, "r") as f:
                            self._animation_metadata[name] = json.load(f)
                    except Exception as e:
                        log_error(f"Error parsing animation.json for '{name}': {e}")
                
                # Fetch png files
                files = [fn for fn in os.listdir(sdir) if fn.lower().endswith(".png")]
                # Natural numeric sorting
                def natural_sort_key(s):
                    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
                files.sort(key=natural_sort_key)
                
                for fn in files:
                    pix = QPixmap(os.path.join(sdir, fn))
                    if not pix.isNull():
                        scaled = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        canvas = QPixmap(128, 128)
                        canvas.fill(Qt.transparent)
                        painter = QPainter(canvas)
                        x = (128 - scaled.width()) // 2
                        y = (128 - scaled.height()) // 2
                        painter.drawPixmap(x, y, scaled)
                        painter.end()
                        frames.append(canvas)
                
                if frames:
                    return frames

        # 2. Check for prefix root files e.g. assets/{name}_*.png
        pattern = os.path.join(self.assets_dir, f"{name}_*.png")
        files = glob.glob(pattern)
        if files:
            def natural_sort_key(s):
                return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
            files.sort(key=natural_sort_key)
            for f in files:
                pix = QPixmap(f)
                if not pix.isNull():
                    scaled = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    canvas = QPixmap(128, 128)
                    canvas.fill(Qt.transparent)
                    painter = QPainter(canvas)
                    x = (128 - scaled.width()) // 2
                    y = (128 - scaled.height()) // 2
                    painter.drawPixmap(x, y, scaled)
                    painter.end()
                    frames.append(canvas)
            if frames:
                return frames

        # 3. Check for single file root image assets/{name}.png
        single_path = os.path.join(self.assets_dir, f"{name}.png")
        if os.path.isfile(single_path):
            pix = QPixmap(single_path)
            if not pix.isNull():
                scaled = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                canvas = QPixmap(128, 128)
                canvas.fill(Qt.transparent)
                painter = QPainter(canvas)
                x = (128 - scaled.width()) // 2
                y = (128 - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                frames.append(canvas)
                return frames
                
        return []

    def get_animation_frames(self, name: str, facing_right: bool = True) -> list:
        """
        Retrieves frame sequence for requested animation name.
        Uses FALLBACK_MAP or 'idle' fallback in case assets are missing.
        Never crashes.
        """
        # Canonicalize lookup names
        lookup_name = name.lower()
        if lookup_name == "sleeping":
            lookup_name = "sleep"
        elif lookup_name == "petted":
            lookup_name = "petting"

        cache_key = (lookup_name, facing_right)
        if cache_key in self._animation_cache:
            return self._animation_cache[cache_key]
            
        # Try dynamic loading
        frames = self._load_dynamic_animation(lookup_name)
        if frames:
            mirrored = [self._mirror_frame(f) for f in frames]
            self._animation_cache[(lookup_name, True)] = frames
            self._animation_cache[(lookup_name, False)] = mirrored
            return frames if facing_right else mirrored
            
        # Look up fallback maps recursively
        if lookup_name in FALLBACK_MAP:
            fb_name = FALLBACK_MAP[lookup_name]
            log_debug(f"Animation '{lookup_name}' not found, falling back to '{fb_name}'")
            return self.get_animation_frames(fb_name, facing_right)
            
        # Hard fallback to preloaded idle
        log_debug(f"Animation '{lookup_name}' and fallbacks missing, default fallback to 'idle'")
        return self.idle_right if facing_right else self.idle_left

    def get_animation_metadata(self, name: str) -> dict:
        """Returns parsed metadata dict or empty dict if none found."""
        return self._animation_metadata.get(name.lower(), {})
