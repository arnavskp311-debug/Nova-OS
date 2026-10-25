# Configuration and paths for NOVA OS
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "nova_os.db"
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"
BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
WALLPAPERS_DIR = DATA_DIR / "wallpapers"
WALLPAPERS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_WALLPAPER_PATH = WALLPAPERS_DIR / "nova_cyber_desktop.png"

APP_NAME = "NOVA OS"
APP_VERSION = "1.1.0-trial"
APP_SUBTITLE = "Cybernetic AI Desktop Environment for Windows"

# Browser settings
BROWSER_HOMEPAGE = "nova://welcome"
DEFAULT_SEARCH_ENGINE = "https://duckduckgo.com/?q="

# Default AI Settings (Optimized for Intel Core i3 / 4 GB RAM)
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:0.5b"
FALLBACK_MODEL = "qwen2.5:1.5b"

# Hardware Profile & Resource Management
TARGET_HARDWARE = "Intel Core i3 / 4 GB RAM / 256 GB SSD"
LOW_RAM_OPTIMIZATIONS = True
MAX_CLIPBOARD_HISTORY = 30
NOTIFICATION_DURATION_MS = 4000

# Safety settings
COMMAND_TIMEOUT_SECONDS = 15
MAX_LOG_ENTRIES = 1000

# Theme accents
ACCENT_COLORS = {
    "Cyber Cyan": "#00f0ff",
    "Neon Violet": "#b026ff",
    "Emerald Matrix": "#00ff88",
    "Solar Amber": "#ffaa00",
    "Crimson Flare": "#ff2a55",
}
DEFAULT_ACCENT = "Cyber Cyan"
