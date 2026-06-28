import subprocess

# Map user variations to macOS applications
APP_MAP = {
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "terminal": "Terminal",
    "spotify": "Spotify",
    "finder": "Finder",
    "safari": "Safari",
    "slack": "Slack",
    "zoom": "zoom.us",
    "discord": "Discord",
    "calculator": "Calculator",
    "textedit": "TextEdit",
    "app store": "App Store"
}

def launch_app(name: str) -> tuple:
    """
    Launches a macOS application by name.
    Returns: (success: bool, app_launched_name: str, message: str)
    """
    app_key = name.lower().strip()
    mac_app_name = APP_MAP.get(app_key)
    
    if not mac_app_name:
        # Fallback to Title case
        mac_app_name = name.title().strip()
        
    try:
        # Run 'open -a AppName' on macOS
        subprocess.Popen(["open", "-a", mac_app_name])
        return True, mac_app_name, f"Successfully launched application: '{mac_app_name}'."
    except Exception as e:
        return False, mac_app_name, f"Failed to open application '{mac_app_name}': {e}"
