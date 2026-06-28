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
