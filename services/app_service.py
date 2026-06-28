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
    Launches a macOS application or opens a URL by name.
    Returns: (success: bool, app_launched_name: str, message: str)
    """
    # Check if name is a URL
    if name.startswith("http://") or name.startswith("https://"):
        try:
            subprocess.Popen(["open", name])
            return True, name, f"Successfully opened URL: {name}"
        except Exception as e:
            return False, name, f"Failed to open URL '{name}': {e}"

    app_key = name.lower().strip()
    mac_app_name = APP_MAP.get(app_key)
    
    if not mac_app_name:
        mac_app_name = name.title().strip()
        
    try:
        subprocess.Popen(["open", "-a", mac_app_name])
        return True, mac_app_name, f"Successfully launched application: '{mac_app_name}'."
    except Exception as e:
        return False, mac_app_name, f"Failed to open application '{mac_app_name}': {e}"

def close_app(name: str) -> tuple:
    """
    Closes a macOS application gracefully using AppleScript.
    Returns: (success: bool, app_closed_name: str, message: str)
    """
    app_key = name.lower().strip()
    mac_app_name = APP_MAP.get(app_key)
    
    if not mac_app_name:
        mac_app_name = name.title().strip()
        
    try:
        cmd = f'quit app "{mac_app_name}"'
        subprocess.run(["osascript", "-e", cmd], capture_output=True, timeout=5)
        return True, mac_app_name, f"Successfully quit application: '{mac_app_name}'."
    except Exception as e:
        return False, mac_app_name, f"Failed to close application '{mac_app_name}': {e}"
