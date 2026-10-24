"""
NOVA OS Safe Google Chrome Integration Core.
Provides read-only data import, URL handoff, and supported extension integration
without tampering with Chrome's files, bypassing security, or touching sensitive tokens.
"""

import os
import sys
import json
import shutil
import logging
import tempfile
import sqlite3
import subprocess
import webbrowser
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from nova.database import (
    add_browser_bookmark, add_browser_bookmarks_batch, delete_imported_bookmarks,
    add_browser_history, add_browser_history_batch, clear_browser_history,
    get_setting, set_setting
)

logger = logging.getLogger("nova.chrome")

CHROME_USER_DATA_DEFAULT = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google", "Chrome", "User Data"
)

class ChromeIntegrationManager:
    """
    Manages safe, read-only interactions with Google Chrome on Windows.
    Enforces strict security isolation:
      - NO password extraction or DPAPI / App-Bound Encryption tampering
      - NO cookie extraction or session hijacking
      - NO in-place modification of Chrome's live databases
      - Reversible, explicit user-controlled data import
    """

    def __init__(self, user_data_path: Optional[str] = None):
        self.user_data_path = user_data_path or CHROME_USER_DATA_DEFAULT
        self.chrome_exe = self.detect_chrome_installation()

    def detect_chrome_installation(self) -> Optional[str]:
        """Locates the Google Chrome executable on standard Windows paths."""
        candidate_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for path in candidate_paths:
            if os.path.isfile(path):
                return path
        return None

    def is_chrome_installed(self) -> bool:
        return self.chrome_exe is not None and os.path.isfile(self.chrome_exe)

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns current integration status and user-granted permissions."""
        connected = get_setting("chrome_connected", False)
        perm_bookmarks = get_setting("chrome_perm_bookmarks", False)
        perm_history = get_setting("chrome_perm_history", False)
        perm_handoff = get_setting("chrome_perm_handoff", True)
        selected_profile = get_setting("chrome_selected_profile", "Default")

        return {
            "installed": self.is_chrome_installed(),
            "chrome_path": self.chrome_exe or "Not Found",
            "connected": connected and self.is_chrome_installed(),
            "perm_bookmarks": perm_bookmarks,
            "perm_history": perm_history,
            "perm_handoff": perm_handoff,
            "selected_profile": selected_profile,
            "user_data_path": self.user_data_path,
        }

    def set_connection_status(self, connected: bool, perm_bookmarks: bool = False, perm_history: bool = False, perm_handoff: bool = True, profile: str = "Default"):
        set_setting("chrome_connected", connected)
        set_setting("chrome_perm_bookmarks", perm_bookmarks)
        set_setting("chrome_perm_history", perm_history)
        set_setting("chrome_perm_handoff", perm_handoff)
        set_setting("chrome_selected_profile", profile)

    def get_available_profiles(self) -> List[Dict[str, Any]]:
        """
        Discovers Chrome user profiles by reading 'Local State' in read-only mode.
        Does not lock, modify, or interfere with Chrome.
        """
        profiles = []
        if not os.path.isdir(self.user_data_path):
            return profiles

        state_file = os.path.join(self.user_data_path, "Local State")
        info_cache = {}

        if os.path.isfile(state_file):
            try:
                with open(state_file, "r", encoding="utf-8", errors="replace") as f:
                    state_data = json.load(f)
                    info_cache = state_data.get("profile", {}).get("info_cache", {})
            except Exception as e:
                logger.warning(f"Could not read Chrome Local State: {e}")

        # Scan folder for profile directories
        for entry in os.listdir(self.user_data_path):
            dir_path = os.path.join(self.user_data_path, entry)
            if not os.path.isdir(dir_path):
                continue

            bm_file = os.path.join(dir_path, "Bookmarks")
            hist_file = os.path.join(dir_path, "History")

            # Check if this directory looks like a Chrome profile
            if entry == "Default" or entry.startswith("Profile ") or os.path.exists(bm_file) or os.path.exists(hist_file):
                human_name = info_cache.get(entry, {}).get("name") or entry
                profiles.append({
                    "id": entry,
                    "name": human_name,
                    "path": dir_path,
                    "has_bookmarks": os.path.isfile(bm_file),
                    "has_history": os.path.isfile(hist_file)
                })

        # Ensure Default is at top if present
        profiles.sort(key=lambda p: (0 if p["id"] == "Default" else 1, p["name"].lower()))
        return profiles

    # ----------------- Safe Read-Only Bookmarks Import -----------------

    def import_bookmarks(self, profile_id: str = "Default") -> Tuple[int, str]:
        """
        Safely imports bookmarks from Chrome's plain-text JSON 'Bookmarks' file.
        Operates strictly in read-only mode.
        """
        status = self.get_connection_status()
        if not status["connected"] or not status["perm_bookmarks"]:
            return 0, "Permission Denied: User has not enabled Chrome bookmarks access."

        bm_path = os.path.join(self.user_data_path, profile_id, "Bookmarks")
        if not os.path.isfile(bm_path):
            return 0, f"No Bookmarks file found in profile '{profile_id}'."

        try:
            with open(bm_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except Exception as e:
            return 0, f"Error reading Bookmarks JSON: {str(e)}"

        roots = data.get("roots", {})
        entries_to_insert = []

        def traverse_nodes(node: dict, folder_name: str):
            node_type = node.get("type")
            if node_type == "url":
                url = node.get("url", "").strip()
                title = node.get("name", "").strip() or url
                if url:
                    entries_to_insert.append((
                        title,
                        url,
                        f"Chrome/{folder_name}",
                        f"Chrome ({profile_id})"
                    ))
            elif node_type == "folder":
                sub_folder = node.get("name", "").strip() or folder_name
                for child in node.get("children", []):
                    traverse_nodes(child, f"{folder_name}/{sub_folder}" if folder_name else sub_folder)

        for root_key in ["bookmark_bar", "other", "synced"]:
            if root_key in roots:
                root_node = roots[root_key]
                display_folder = root_node.get("name", root_key.replace("_", " ").title())
                for child in root_node.get("children", []):
                    traverse_nodes(child, display_folder)

        imported_count = add_browser_bookmarks_batch(entries_to_insert)
        return imported_count, f"Successfully imported {imported_count} bookmarks from Chrome ({profile_id})."

    # ----------------- Safe Read-Only History Import -----------------

    def import_history(self, profile_id: str = "Default", limit: int = 150) -> Tuple[int, str]:
        """
        Safely imports browsing history from Chrome's SQLite database.
        Copies the file to a temporary location first to guarantee NO lock contention
        and zero risk of corrupting Chrome's live databases.
        """
        status = self.get_connection_status()
        if not status["connected"] or not status["perm_history"]:
            return 0, "Permission Denied: User has not enabled Chrome history access."

        hist_path = os.path.join(self.user_data_path, profile_id, "History")
        if not os.path.isfile(hist_path):
            return 0, f"No History database found in profile '{profile_id}'."

        # Create temporary read-only copy
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
            temp_db_path = tmp_file.name

        entries_to_insert = []
        try:
            shutil.copyfile(hist_path, temp_db_path)
            conn = sqlite3.connect(f"file:{temp_db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Chrome History stores URLs and titles in 'urls' table
            cursor.execute(
                "SELECT title, url, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()

            for title, url, _ in rows:
                if url and not url.startswith("chrome://"):
                    entries_to_insert.append((
                        title or url,
                        url,
                        f"Chrome ({profile_id})"
                    ))

            imported_count = add_browser_history_batch(entries_to_insert)
            return imported_count, f"Successfully imported {imported_count} recent history items from Chrome ({profile_id})."
        except Exception as e:
            return 0, f"Error safely querying Chrome history: {str(e)}"
        finally:
            if os.path.isfile(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except OSError:
                    pass

    # ----------------- Bi-Directional URL Handoff -----------------

    def open_url_in_chrome(self, url: str, profile_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Safely launches the given URL in Google Chrome.
        Uses standard command line invocation without administrator privileges.
        """
        status = self.get_connection_status()
        if not status["perm_handoff"]:
            return False, "URL handoff permission is disabled in NOVA Browser settings."

        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return False, "Invalid URL format for external handoff."

        target_profile = profile_id or status.get("selected_profile")

        if self.chrome_exe and os.path.isfile(self.chrome_exe):
            cmd = [self.chrome_exe]
            if target_profile and target_profile != "Default":
                cmd.append(f"--profile-directory={target_profile}")
            cmd.append(url)
            try:
                subprocess.Popen(cmd)
                return True, f"URL dispatched to Google Chrome (Profile: {target_profile or 'Default'})."
            except Exception as e:
                logger.warning(f"Failed to launch Chrome directly: {e}")

        # Fallback to system default handler
        try:
            webbrowser.open(url)
            return True, "URL opened via system default browser."
        except Exception as e:
            return False, f"Could not launch browser: {str(e)}"

    # ----------------- Extension & Native Messaging Documentation -----------------

    @staticmethod
    def get_native_messaging_info() -> Dict[str, Any]:
        """
        Returns official Google Chrome Native Messaging specification details,
        host manifest template, and communication protocol guidelines.
        """
        manifest_template = {
            "name": "com.nova.os.browser.bridge",
            "description": "NOVA OS Safe Chrome Companion Bridge",
            "path": r"C:\Users\<user>\Desktop\Project\O.S\nova\native_host.bat",
            "type": "stdio",
            "allowed_origins": [
                "chrome-extension://<EXTENSION_ID_HERE>/"
            ]
        }

        return {
            "name": "com.nova.os.browser.bridge",
            "manifest_json": json.dumps(manifest_template, indent=2),
            "registry_key": r"HKCU\Software\Google\Chrome\NativeMessagingHosts\com.nova.os.browser.bridge",
            "protocol_summary": (
                "Official Chrome Native Messaging allows a WebExtension in Chrome to exchange "
                "JSON messages with a registered local native host via standard input (stdin) "
                "and standard output (stdout), with each message preceded by its 32-bit length.\n\n"
                "This official interface enables: \n"
                "  • Sending the currently active Chrome tab URL to NOVA Browser.\n"
                "  • Opening a bookmark or link from NOVA Browser directly into an active Chrome tab.\n"
                "  • Zero privilege elevation or security compromises."
            ),
            "limitations": (
                "Chrome extension security policies strictly prevent extensions from exporting "
                "raw session cookies with 'HttpOnly' flags, protected authentication tokens, "
                "or saved master credentials without explicit interactive authentication."
            )
        }

    @staticmethod
    def get_security_disclosures() -> Dict[str, Any]:
        """
        Explains supported versus unsupported features, Chrome's security model,
        and safe alternatives.
        """
        return {
            "supported": [
                "Read-only Bookmarks import via standard JSON parser.",
                "Read-only History snapshot import via temporary non-locking copy.",
                "Bi-directional URL Handoff (Open current tab in Chrome / Open link in NOVA).",
                "Reversible data management (One-click purge of all imported items without touching Chrome or native NOVA items).",
                "Official Chrome Native Messaging bridge manifest and protocol integration.",
                "Completely separate browsing profile, cookies, and cache in data/browser_profile/."
            ],
            "unsupported_and_blocked": [
                "Extracting passwords from Chrome's 'Login Data' (Blocked: Protected by Windows DPAPI and Chrome App-Bound Encryption).",
                "Copying session cookies or auth tokens from 'Network/Cookies' (Blocked: Violates browser isolation and session security).",
                "Modifying or deleting Chrome's original profile files or databases (Blocked: Never touches original files).",
                "Bypassing active database locks while Chrome is running (Blocked: Uses isolated temporary copies only)."
            ],
            "safe_alternatives": (
                "1. If you need your authenticated session (e.g., Google Account, GitHub, Banking), "
                "simply click 'Open in Chrome' to seamlessly view the page in your existing authenticated Chrome session.\n"
                "2. Alternatively, log into the website directly inside NOVA Browser. NOVA Browser uses an isolated Qt WebEngine "
                "profile stored in its own project directory that keeps your login active safely."
            )
        }
