"""
NOVA OS // WINDOWS APPLICATION DISCOVERY & BRIDGING SUBSYSTEM.
Discovers, launches, monitors, and manages native Windows desktop applications,
enabling full Windows ecosystem access directly from NOVA OS and Pajama scripts.
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("nova.windows_apps")


# =============================================================================
# Built-in Standard Windows Utilities
# =============================================================================

STANDARD_WINDOWS_TOOLS = [
    {
        "name": "Calculator",
        "alias": "calc",
        "path": "calc.exe",
        "icon": "🧮",
        "category": "Tools",
        "description": "Windows standard numeric and scientific calculator"
    },
    {
        "name": "Notepad",
        "alias": "notepad",
        "path": "notepad.exe",
        "icon": "📝",
        "category": "Productivity",
        "description": "Windows plain-text note and document editor"
    },
    {
        "name": "Paint",
        "alias": "paint",
        "path": "mspaint.exe",
        "icon": "🎨",
        "category": "Media",
        "description": "Windows classic drawing and image editing suite"
    },
    {
        "name": "File Explorer",
        "alias": "explorer",
        "path": "explorer.exe",
        "icon": "📁",
        "category": "System",
        "description": "Windows native file browser and folder explorer"
    },
    {
        "name": "Task Manager",
        "alias": "taskmgr",
        "path": "taskmgr.exe",
        "icon": "📊",
        "category": "System",
        "description": "Windows hardware, process, and performance monitor"
    },
    {
        "name": "Command Prompt",
        "alias": "cmd",
        "path": "cmd.exe",
        "icon": "💻",
        "category": "System",
        "description": "Windows standard command shell"
    },
    {
        "name": "Windows PowerShell",
        "alias": "powershell",
        "path": "powershell.exe",
        "icon": "💻",
        "category": "System",
        "description": "Windows PowerShell command scripting shell"
    },
    {
        "name": "Snipping Tool",
        "alias": "snip",
        "path": "snippingtool.exe",
        "icon": "✂️",
        "category": "Tools",
        "description": "Windows screen capture and annotation utility"
    },
    {
        "name": "Control Panel",
        "alias": "control",
        "path": "control.exe",
        "icon": "⚙️",
        "category": "System",
        "description": "Windows configuration and hardware settings"
    },
    {
        "name": "Disk Cleanup",
        "alias": "cleanmgr",
        "path": "cleanmgr.exe",
        "icon": "🧹",
        "category": "System",
        "description": "Windows drive and temporary file cleanup utility"
    },
    {
        "name": "Resource Monitor",
        "alias": "resmon",
        "path": "resmon.exe",
        "icon": "📈",
        "category": "System",
        "description": "Windows detailed CPU, memory, and network monitor"
    },
]


class WindowsAppInfo:
    """Represents an installed Windows application."""

    def __init__(
        self,
        name: str,
        path: str,
        icon: str = "🪟",
        category: str = "Tools",
        alias: str = "",
        description: str = "",
        is_system: bool = False
    ):
        self.name = name
        self.path = path
        self.icon = icon
        self.category = category
        self.alias = alias or name.lower().replace(" ", "")
        self.description = description
        self.is_system = is_system

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "icon": self.icon,
            "category": self.category,
            "alias": self.alias,
            "description": self.description,
            "is_system": self.is_system
        }


class WindowsAppManager:
    """Discovers, indexes, launches, and monitors all Windows applications."""

    def __init__(self, shortcuts_file: str = "data/desktop_shortcuts.json"):
        self.shortcuts_file = shortcuts_file
        self._cached_apps: Optional[List[WindowsAppInfo]] = None

    def discover_apps(self, force_refresh: bool = False) -> List[WindowsAppInfo]:
        """Scans Windows Start Menu, System directories, and Program Files."""
        if self._cached_apps is not None and not force_refresh:
            return self._cached_apps

        apps: List[WindowsAppInfo] = []
        seen_names = set()

        # 1. Add standard Windows utilities
        for tool in STANDARD_WINDOWS_TOOLS:
            app = WindowsAppInfo(
                name=tool["name"],
                path=tool["path"],
                icon=tool["icon"],
                category=tool["category"],
                alias=tool["alias"],
                description=tool["description"],
                is_system=True
            )
            apps.append(app)
            seen_names.add(tool["name"].lower())

        # 2. Scan Start Menu directories
        start_menu_dirs = [
            Path(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"),
        ]
        user_appdata = os.environ.get("APPDATA")
        if user_appdata:
            start_menu_dirs.append(Path(user_appdata) / r"Microsoft\Windows\Start Menu\Programs")

        for s_dir in start_menu_dirs:
            if not s_dir.exists():
                continue
            try:
                for item in s_dir.rglob("*.lnk"):
                    name = item.stem
                    lower_name = name.lower()

                    # Filter out uninstaller or helper shortcuts
                    if any(w in lower_name for w in ("uninstall", "remove", "help", "website", "readme", "license", "documentation")):
                        continue
                    if lower_name in seen_names:
                        continue

                    seen_names.add(lower_name)
                    cat, icon = self._categorize_app(name)
                    apps.append(WindowsAppInfo(
                        name=name,
                        path=str(item.resolve()),
                        icon=icon,
                        category=cat,
                        alias=lower_name.replace(" ", "")
                    ))
            except Exception as e:
                logger.warning(f"Error scanning Start Menu directory {s_dir}: {e}")

        # 3. Scan Common Chrome and Edge paths if not already found
        common_browsers = [
            ("Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe", "🌐", "Browsers"),
            ("Google Chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "🌐", "Browsers"),
            ("Microsoft Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "🌐", "Browsers"),
            ("Mozilla Firefox", r"C:\Program Files\Mozilla Firefox\firefox.exe", "🦊", "Browsers"),
            ("VS Code", os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"), "💻", "Development"),
        ]
        for b_name, b_path, b_icon, b_cat in common_browsers:
            if b_name.lower() not in seen_names and os.path.exists(b_path):
                seen_names.add(b_name.lower())
                apps.append(WindowsAppInfo(
                    name=b_name,
                    path=b_path,
                    icon=b_icon,
                    category=b_cat,
                    alias=b_name.lower().replace(" ", "")
                ))

        self._cached_apps = apps
        return apps

    def _categorize_app(self, name: str) -> Tuple[str, str]:
        """Determines category and emoji icon based on application name."""
        nl = name.lower()
        if any(w in nl for w in ("chrome", "edge", "firefox", "browser", "brave", "opera")):
            return "Browsers", "🌐"
        if any(w in nl for w in ("code", "visual studio", "python", "pycharm", "git", "terminal", "powershell", "cmd", "idle")):
            return "Development", "💻"
        if any(w in nl for w in ("word", "excel", "powerpoint", "office", "notepad", "onenote", "pdf", "reader", "writer", "document")):
            return "Productivity", "📝"
        if any(w in nl for w in ("spotify", "vlc", "media", "music", "paint", "audio", "player", "sound", "stream", "video")):
            return "Media", "🎵"
        if any(w in nl for w in ("steam", "epic", "game", "xbox", "riot", "blizzard", "play")):
            return "Gaming", "🎮"
        if any(w in nl for w in ("settings", "manager", "cleanup", "security", "control", "system", "disk", "hardware")):
            return "System", "⚙️"
        return "Tools", "🪟"

    def launch_app(self, target: str) -> Tuple[bool, str]:
        """
        Launches an application by name, alias, or path safely using Windows startfile.
        Returns (success: bool, message: str).
        """
        target_clean = target.strip()
        target_lower = target_clean.lower().replace(" ", "")

        # 1. Check exact path
        if os.path.exists(target_clean):
            try:
                os.startfile(target_clean)
                return True, f"Launched Windows application: {target_clean}"
            except Exception as e:
                return False, f"Failed to start executable {target_clean}: {e}"

        # 2. Check cached apps by alias or name
        apps = self.discover_apps()
        for app in apps:
            if target_lower in (app.alias, app.name.lower().replace(" ", "")):
                try:
                    os.startfile(app.path)
                    return True, f"Launched {app.name} ({app.path})"
                except Exception as e:
                    return False, f"Error launching {app.name}: {e}"

        # 3. Check partial match
        for app in apps:
            if target_lower in app.name.lower().replace(" ", ""):
                try:
                    os.startfile(app.path)
                    return True, f"Launched {app.name} ({app.path})"
                except Exception as e:
                    return False, f"Error launching {app.name}: {e}"

        # 4. Fallback: try direct Windows start command
        try:
            os.startfile(target_clean)
            return True, f"Dispatched {target_clean} to Windows handler"
        except Exception as e:
            return False, f"Application '{target}' not found on this system ({e})"

    def is_process_running(self, name_or_alias: str) -> bool:
        """Returns True if a process matching the name or alias is active."""
        if not psutil:
            return False
        query = name_or_alias.lower().replace(".exe", "").strip()
        try:
            for p in psutil.process_iter(['name']):
                p_name = p.info.get('name', '').lower()
                if query in p_name:
                    return True
        except Exception:
            pass
        return False

    def list_active_processes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns top active processes sorted by memory consumption."""
        if not psutil:
            return []
        proc_list = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    mem_bytes = p.info.get('memory_info').rss if p.info.get('memory_info') else 0
                    mem_mb = round(mem_bytes / (1024 * 1024), 1)
                    proc_list.append({
                        "pid": p.info['pid'],
                        "name": p.info.get('name', 'Unknown'),
                        "memory_mb": mem_mb,
                        "cpu": p.info.get('cpu_percent', 0.0) or 0.0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Error enumerating processes: {e}")

        # Sort descending by memory usage
        proc_list.sort(key=lambda x: x["memory_mb"], reverse=True)
        return proc_list[:limit]

    def terminate_process(self, pid_or_name: Any) -> Tuple[bool, str]:
        """Terminates a process safely by PID or name."""
        if not psutil:
            return False, "psutil not available"

        try:
            if isinstance(pid_or_name, int) or str(pid_or_name).isdigit():
                pid = int(pid_or_name)
                proc = psutil.Process(pid)
                name = proc.name()
                proc.terminate()
                return True, f"Terminated process {name} (PID: {pid})"
            else:
                target_name = str(pid_or_name).lower().strip()
                killed = 0
                for p in psutil.process_iter(['pid', 'name']):
                    if target_name in p.info['name'].lower():
                        p.terminate()
                        killed += 1
                if killed > 0:
                    return True, f"Terminated {killed} process(es) matching '{pid_or_name}'"
                return False, f"No process found matching '{pid_or_name}'"
        except Exception as e:
            return False, f"Failed to terminate process: {e}"

    def pin_to_desktop(self, app_info: WindowsAppInfo) -> Tuple[bool, str]:
        """Pins a Windows application shortcut onto the NOVA OS desktop."""
        if not os.path.exists(self.shortcuts_file):
            return False, "Shortcuts file not found"

        try:
            with open(self.shortcuts_file, "r", encoding="utf-8") as f:
                shortcuts = json.load(f)

            # Check if already pinned
            for s in shortcuts:
                if s.get("title") == app_info.name or s.get("target") == app_info.path:
                    return False, f"'{app_info.name}' is already pinned to the desktop."

            # Calculate next grid slot
            existing_coords = {(s.get("x", 0), s.get("y", 0)) for s in shortcuts}
            x, y = 30, 30
            while (x, y) in existing_coords:
                y += 95
                if y > 500:
                    y = 30
                    x += 95

            new_entry = {
                "id": f"win_{abs(hash(app_info.name)) % 1000000:06d}",
                "title": app_info.name,
                "icon": app_info.icon,
                "type": "file" if os.path.exists(app_info.path) else "app",
                "target": app_info.path,
                "x": x,
                "y": y
            }
            shortcuts.append(new_entry)

            with open(self.shortcuts_file, "w", encoding="utf-8") as f:
                json.dump(shortcuts, f, indent=2, ensure_ascii=False)

            return True, f"Successfully pinned '{app_info.name}' to NOVA OS desktop!"
        except Exception as e:
            return False, f"Failed to pin shortcut: {e}"


# Singleton instance
_windows_app_manager: Optional[WindowsAppManager] = None

def get_windows_app_manager() -> WindowsAppManager:
    global _windows_app_manager
    if _windows_app_manager is None:
        _windows_app_manager = WindowsAppManager()
    return _windows_app_manager
