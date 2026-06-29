import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database Config
DB_PATH = os.path.join(BASE_DIR, "mochi_memory.db")

# LLM Backend settings
ACTIVE_BACKEND = "ollama"  # Default active backend
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:4b"  # Fallback model

# Focus Mode Applications List
FOCUS_APPS = [
    "Visual Studio Code",
    "Xcode",
    "Terminal",
    "PyCharm",
    "IntelliJ IDEA",
    "CLion",
    "WebStorm",
    "Android Studio"
]

# Logging Configuration
LOG_LEVEL = "INFO"  # Levels: DEBUG, INFO, WARN, ERROR
_LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}

def log_message(level: str, msg: str):
    target_level = _LEVELS.get(LOG_LEVEL, 1)
    current_level = _LEVELS.get(level, 1)
    if current_level >= target_level:
        print(f"[{level}] {msg}")

def log_debug(msg: str): log_message("DEBUG", msg)
def log_info(msg: str): log_message("INFO", msg)
def log_warn(msg: str): log_message("WARN", msg)
def log_error(msg: str): log_message("ERROR", msg)
