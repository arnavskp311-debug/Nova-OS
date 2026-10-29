"""
Default Application Associations Subsystem for NOVA OS.
Maps file extensions to native NOVA apps or external Windows applications.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from nova.config import DATA_DIR

ASSOC_FILE = DATA_DIR / "file_associations.json"

DEFAULT_ASSOCIATIONS = {
    ".pj": "pajama",
    ".txt": "notes",
    ".md": "notes",
    ".log": "notes",
    ".py": "pajama",
    ".json": "notes",
    ".csv": "notes",
    ".png": "fileviewer",
    ".jpg": "fileviewer",
    ".jpeg": "fileviewer",
    ".gif": "fileviewer",
    ".html": "browser",
    ".htm": "browser",
    ".url": "browser",
    ".pdf": "browser"
}

class FileAssociations:
    """Manages file type to application bindings."""

    @classmethod
    def get_associations(cls) -> Dict[str, str]:
        if not ASSOC_FILE.exists():
            cls._save(DEFAULT_ASSOCIATIONS)
            return dict(DEFAULT_ASSOCIATIONS)
        try:
            with open(ASSOC_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(DEFAULT_ASSOCIATIONS)

    @classmethod
    def _save(cls, data: Dict[str, str]):
        try:
            with open(ASSOC_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def get_app_for_file(cls, filepath: str) -> str:
        """Returns the app_id registered for this file's extension."""
        ext = Path(filepath).suffix.lower()
        assocs = cls.get_associations()
        return assocs.get(ext, "notes")

    @classmethod
    def set_association(cls, extension: str, app_id: str):
        """Sets or overrides a file extension association."""
        if not extension.startswith("."):
            extension = f".{extension}"
        assocs = cls.get_associations()
        assocs[extension.lower()] = app_id
        cls._save(assocs)
