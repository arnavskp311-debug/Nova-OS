"""
Multi-User Accounts & Profile Isolation Subsystem for NOVA OS.
Manages user accounts (Admin, Standard, Guest), profile switching,
and per-user data directory sandboxing.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from nova.config import DATA_DIR

USERS_FILE = DATA_DIR / "users.json"
USER_DATA_ROOT = DATA_DIR / "user_profiles"

class UserManager:
    """Manages system users and user profile isolation."""

    _current_user: str = "nova_admin"

    DEFAULT_PROFILES = [
        {
            "username": "nova_admin",
            "display_name": "Nova Administrator",
            "role": "admin",
            "avatar": "🛡️",
            "pin": "0000"
        },
        {
            "username": "cyber_dev",
            "display_name": "Cyber Developer",
            "role": "standard",
            "avatar": "⚡",
            "pin": "1234"
        },
        {
            "username": "guest",
            "display_name": "Guest Explorer",
            "role": "guest",
            "avatar": "👤",
            "pin": ""
        }
    ]

    @classmethod
    def init_users(cls):
        """Initializes user profiles store if not exists."""
        USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        if not USERS_FILE.exists():
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump({"active_user": "nova_admin", "users": cls.DEFAULT_PROFILES}, f, indent=2)

    @classmethod
    def get_users(cls) -> List[Dict[str, Any]]:
        """Returns all registered user accounts."""
        cls.init_users()
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("users", cls.DEFAULT_PROFILES)
        except Exception:
            return cls.DEFAULT_PROFILES

    @classmethod
    def get_current_user(cls) -> Dict[str, Any]:
        """Returns metadata for the currently active user."""
        users = cls.get_users()
        for u in users:
            if u["username"] == cls._current_user:
                return u
        return users[0]

    @classmethod
    def switch_user(cls, username: str) -> bool:
        """Switches the active user profile."""
        users = cls.get_users()
        for u in users:
            if u["username"] == username:
                cls._current_user = username
                # Persist active user
                try:
                    with open(USERS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["active_user"] = username
                    with open(USERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    pass
                return True
        return False

    @classmethod
    def get_user_home_dir(cls, username: Optional[str] = None) -> Path:
        """Returns the isolated home directory path for a user."""
        uname = username or cls._current_user
        path = USER_DATA_ROOT / uname
        path.mkdir(parents=True, exist_ok=True)
        return path
