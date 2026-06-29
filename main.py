import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from assets import PetAssets
from pet import DesktopPet

def main():
    # Enable high DPI scaling (must be set before QApplication is created)
    from PyQt5.QtCore import Qt
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    from config.settings import log_info, log_debug
    log_info("Starting Mochi...")
    
    # Hide the macOS Dock icon programmatically using PyObjC Cocoa
    if sys.platform == 'darwin':
        try:
            import Cocoa
            # NSApplicationActivationPolicyAccessory = 1 (removes from dock, retains overlay)
            Cocoa.NSApp.setActivationPolicy_(1)
        except Exception as e:
            log_debug(f"Failed to set Cocoa activation policy: {e}")
    
    # Establish project directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')
    
    try:
        # Load assets
        assets = PetAssets(assets_dir)
        
        # Initialize and show pet
        pet = DesktopPet(assets)
        pet.show()
        pet.raise_()
        pet.activateWindow()
        log_debug("Pet window shown, raised, and activated.")
        
        sys.exit(app.exec_())
        
    except FileNotFoundError as e:
        print("\n" + "="*50)
        print("ERROR: MISSING ASSETS")
        print("="*50)
        print(e)
        print("="*50 + "\n")
        
        # Show a friendly GUI dialog explaining the issue
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Missing Desktop Pet Assets")
        msg.setText("Please add your cropped pet image files first.")
        msg.setInformativeText(
            f"We couldn't locate all required frames in:\n\n{assets_dir}\n\n"
            "Please ensure the following files exist in that directory:\n"
            "- idle_1.png to idle_4.png\n"
            "- walk_1.png to walk_6.png\n"
            "- fall.png\n"
            "- lie.png\n"
            "- sleep.png"
        )
        msg.exec_()
        sys.exit(1)
        
    except Exception as e:
        print(f"An unexpected error occurred during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
