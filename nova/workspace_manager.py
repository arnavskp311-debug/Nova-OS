"""
Workspace Manager for NOVA OS.
Coordinates specialized workspace profiles (Study, Coding, Research, Personal, Entertainment),
pinned applications, and personalized visual themes.
"""

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from nova.database import (
    get_workspaces, get_workspace, set_active_workspace,
    create_workspace, delete_workspace
)

logger = logging.getLogger("nova.workspace")


class WorkspaceManager(QObject):
    """
    Manages loading, switching, and persisting workspace profiles.
    Note: Workspace profiles organize application workflows and layouts within NOVA OS;
    they do not isolate Windows processes or replace operating system accounts.
    """
    workspace_switched = Signal(dict)  # Emits new active workspace dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_workspace: Optional[Dict[str, Any]] = None
        self.load_active_workspace()

    def get_all_workspaces(self) -> List[Dict[str, Any]]:
        return get_workspaces()

    def get_workspace_by_id(self, ws_id: str) -> Optional[Dict[str, Any]]:
        return get_workspace(ws_id)

    def load_active_workspace(self) -> Dict[str, Any]:
        all_ws = self.get_all_workspaces()
        for ws in all_ws:
            if ws.get("is_active"):
                self._active_workspace = ws
                return ws
        if all_ws:
            self._active_workspace = all_ws[0]
            set_active_workspace(self._active_workspace["id"])
            return self._active_workspace
        return {
            "id": "study",
            "name": "Study Workspace",
            "description": "Focus • Learn • Achieve",
            "theme": "Cyber Cyan",
            "pinned_apps": ["browser", "notes", "files", "chat"],
            "is_active": 1
        }

    def switch_to(self, ws_id: str) -> bool:
        ws = get_workspace(ws_id)
        if not ws:
            return False
        set_active_workspace(ws_id)
        self._active_workspace = ws
        self.workspace_switched.emit(ws)
        logger.info(f"Switched to workspace '{ws['name']}' ({ws_id})")
        return True

    def create_custom(self, ws_id: str, name: str, description: str, theme: str, pinned_apps: list) -> bool:
        ok = create_workspace(ws_id, name, description, theme, pinned_apps)
        if ok:
            logger.info(f"Created custom workspace: {name}")
        return ok

    def remove_custom(self, ws_id: str) -> bool:
        if ws_id in ("study", "coding", "research", "personal", "entertainment"):
            return False  # Protect built-in archetypes
        return delete_workspace(ws_id)
