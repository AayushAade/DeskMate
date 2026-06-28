import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTransform, QPainter

class PetAssets:
    def __init__(self, assets_dir=None):
        if assets_dir is None:
            # Default to 'assets' folder in the same directory as this script
            assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        
        self.assets_dir = assets_dir
        
        # Lists to hold frames (Right-facing by default, Left-facing will be mirrored)
        self.idle_right = []
        self.idle_left = []
        
        self.walk_right = []
        self.walk_left = []
        
        # Sliced animations
        self.typing_right = []
        self.typing_left = []
        
        self.petted_right = []
        self.petted_left = []
        
        # Single frame states (mapped to lists for consistency in anim loop)
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
            
        # Scale preserving aspect ratio
        scaled = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Centering canvas to enforce uniform 128x128 boundaries across all animation states
        canvas = QPixmap(128, 128)
        canvas.fill(Qt.transparent)
        
        painter = QPainter(canvas)
        x = (128 - scaled.width()) // 2
        y = (128 - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        
        return canvas

    def _mirror_frame(self, pixmap):
        # Flips the pixmap horizontally
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

        print("Successfully loaded all assets:")
        print(f" - Idle: {len(self.idle_right)} frames")
        print(f" - Walk: {len(self.walk_right)} frames")
        print(f" - Typing: {len(self.typing_right)} frames")
        print(f" - Petting: {len(self.petted_right)} frames")
        print(f" - Fall: {len(self.fall_right)} frame(s)")
        print(f" - Lie: {len(self.lie_right)} frame(s)")
        print(f" - Sleep: {len(self.sleep_right)} frame(s)")
        print(f"Flipped left-facing variations created.")
