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
DEFAULT_WALLPAPER_PATH = (WALLPAPERS_DIR / "nova_deep_space.png") if (WALLPAPERS_DIR / "nova_deep_space.png").exists() else (WALLPAPERS_DIR / "nova_cyber_desktop.png")

APP_NAME = "NOVA OS"
APP_VERSION = "1.1.0-trial"
APP_SUBTITLE = "Personalized Premium Space Desktop"

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
    "Cosmic Cyan": "#00d2e6",
    "Ice Blue": "#38bdf8",
    "Stellar Violet": "#a855f7",
    "Emerald Aurora": "#10b981",
    "Solar Amber": "#f59e0b",
    "Cyber Cyan": "#00f0ff",
}
DEFAULT_ACCENT = "Cosmic Cyan"

# Dedicated Research Agent Workspace
WORKSPACE_DIR = DATA_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_REPORTS_DIR = WORKSPACE_DIR / "reports"
WORKSPACE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_NOTES_DIR = WORKSPACE_DIR / "notes"
WORKSPACE_NOTES_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DOWNLOADS_DIR = WORKSPACE_DIR / "downloads"
WORKSPACE_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_RESEARCH_DIR = WORKSPACE_DIR / "research"
WORKSPACE_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_TEMP_DIR = WORKSPACE_DIR / "temp"
WORKSPACE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Autonomous Research Agent Constants
MAX_RESEARCH_PAGES = 10
MAX_DOWNLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB max per downloaded file
MAX_TEXT_EXTRACT_CHARS = 6000             # Text extraction limit to prevent RAM bloat
WEB_REQUEST_TIMEOUT = 10                  # seconds
PERMITTED_RESEARCH_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".pdf", ".html", ".log"}
PROHIBITED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".dll", ".scr", ".pif", ".com", ".reg"}
