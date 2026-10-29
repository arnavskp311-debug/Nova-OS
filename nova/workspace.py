"""
NOVA OS Dedicated Research Workspace Manager.
Provides isolated, audited, and anti-traversal filesystem operations
strictly confined to data/workspace/ for the Autonomous Research Agent.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from nova.config import (
    WORKSPACE_DIR, WORKSPACE_REPORTS_DIR, WORKSPACE_NOTES_DIR,
    WORKSPACE_DOWNLOADS_DIR, WORKSPACE_RESEARCH_DIR, WORKSPACE_TEMP_DIR,
    MAX_DOWNLOAD_SIZE_BYTES
)
from nova.permissions import get_permission_enforcer, Capability, PermissionDeniedSecurityError

logger = logging.getLogger("nova.workspace")


class ResearchWorkspace:
    """
    Manages all research artifacts, notes, reports, and downloads
    within the dedicated, sandboxed workspace boundary.
    """

    SUBFOLDERS = {
        "reports": WORKSPACE_REPORTS_DIR,
        "notes": WORKSPACE_NOTES_DIR,
        "downloads": WORKSPACE_DOWNLOADS_DIR,
        "research": WORKSPACE_RESEARCH_DIR,
        "temp": WORKSPACE_TEMP_DIR,
    }

    def __init__(self, root_dir: Path = WORKSPACE_DIR):
        self.root_dir = root_dir.resolve()
        self.enforcer = get_permission_enforcer()
        self.ensure_directories()

    def ensure_directories(self):
        """Creates all required workspace subdirectories if missing."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        for folder_path in self.SUBFOLDERS.values():
            folder_path.mkdir(parents=True, exist_ok=True)

    def write_file(
        self,
        subfolder: str,
        filename: str,
        content: Union[str, bytes],
        encoding: str = "utf-8"
    ) -> Path:
        """
        Safely writes content into the designated workspace subfolder.
        Enforces path boundary and file extension restrictions.
        """
        self.enforcer.require_permission(Capability.WORKSPACE_WRITE, f"{subfolder}/{filename}")

        folder_key = subfolder.strip().lower()
        target_dir = self.SUBFOLDERS.get(folder_key)
        if not target_dir:
            # Check if subfolder is relative path inside workspace
            candidate = (self.root_dir / subfolder).resolve()
            if candidate.is_relative_to(self.root_dir):
                target_dir = candidate
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise PermissionDeniedSecurityError(f"Unauthorized workspace subfolder '{subfolder}'.")

        target_file = target_dir / filename
        is_valid, reason, resolved = self.enforcer.validate_fs_path(target_file, mode="write")
        if not is_valid or not resolved:
            raise PermissionDeniedSecurityError(f"Workspace write denied: {reason}")

        # Check payload size
        size = len(content.encode(encoding)) if isinstance(content, str) else len(content)
        if size > MAX_DOWNLOAD_SIZE_BYTES * 2:
            raise ValueError(f"Content size ({size} bytes) exceeds workspace limit.")

        # Atomic write
        temp_file = target_dir / f".tmp_{resolved.name}"
        try:
            if isinstance(content, str):
                temp_file.write_text(content, encoding=encoding)
            else:
                temp_file.write_bytes(content)
            temp_file.replace(resolved)
        except Exception:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise

        logger.info(f"Workspace file written: {resolved.relative_to(self.root_dir)} ({size} bytes)")
        return resolved

    def read_file(self, target_path: Union[Path, str], encoding: str = "utf-8") -> str:
        """
        Safely reads a text file from within the workspace.
        Enforces canonical sandbox confinement.
        """
        self.enforcer.require_permission(Capability.WORKSPACE_READ, str(target_path))

        is_valid, reason, resolved = self.enforcer.validate_fs_path(target_path, mode="read")
        if not is_valid or not resolved:
            raise PermissionDeniedSecurityError(f"Workspace read denied: {reason}")

        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Workspace file not found: {resolved}")

        return resolved.read_text(encoding=encoding, errors="replace")

    def list_files(self, subfolder: str = "") -> List[Dict[str, Any]]:
        """Lists files within the workspace or a specified subfolder."""
        self.enforcer.require_permission(Capability.WORKSPACE_READ, subfolder or "root")

        if subfolder:
            folder_key = subfolder.strip().lower()
            target_dir = self.SUBFOLDERS.get(folder_key)
            if not target_dir:
                candidate = (self.root_dir / subfolder).resolve()
                if candidate.is_relative_to(self.root_dir):
                    target_dir = candidate
                else:
                    return []
            scan_dirs = [target_dir]
        else:
            scan_dirs = list(self.SUBFOLDERS.values())

        results = []
        for sdir in scan_dirs:
            if not sdir.exists():
                continue
            for item in sorted(sdir.iterdir()):
                if item.is_file() and not item.name.startswith("."):
                    stat = item.stat()
                    results.append({
                        "name": item.name,
                        "subfolder": sdir.name,
                        "path": str(item.resolve()),
                        "relative_path": str(item.relative_to(self.root_dir)),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        return results

    def delete_file(self, target_path: Union[Path, str]) -> bool:
        """Safely removes a file inside the workspace."""
        self.enforcer.require_permission(Capability.WORKSPACE_WRITE, str(target_path))

        is_valid, reason, resolved = self.enforcer.validate_fs_path(target_path, mode="write")
        if not is_valid or not resolved:
            raise PermissionDeniedSecurityError(f"Workspace delete denied: {reason}")

        if resolved.exists() and resolved.is_file():
            resolved.unlink()
            logger.info(f"Workspace file deleted: {resolved.name}")
            return True
        return False

    def cleanup_temp(self) -> int:
        """Purges transient temporary files inside data/workspace/temp/."""
        purged = 0
        if WORKSPACE_TEMP_DIR.exists():
            for f in WORKSPACE_TEMP_DIR.iterdir():
                try:
                    if f.is_file():
                        f.unlink()
                        purged += 1
                    elif f.is_dir():
                        shutil.rmtree(f)
                        purged += 1
                except Exception as e:
                    logger.warning(f"Failed to purge temp file {f.name}: {e}")
        return purged

    def get_workspace_stats(self) -> Dict[str, Any]:
        """Returns storage metrics and item counts across workspace folders."""
        stats = {
            "root": str(self.root_dir),
            "total_files": 0,
            "total_bytes": 0,
            "folders": {}
        }
        for name, folder in self.SUBFOLDERS.items():
            count = 0
            size = 0
            if folder.exists():
                for item in folder.iterdir():
                    if item.is_file():
                        count += 1
                        size += item.stat().st_size
            stats["folders"][name] = {"count": count, "size_bytes": size}
            stats["total_files"] += count
            stats["total_bytes"] += size

        # Free space on host drive
        try:
            usage = shutil.disk_usage(self.root_dir)
            stats["free_disk_bytes"] = usage.free
        except Exception:
            stats["free_disk_bytes"] = 0

        return stats


_workspace_instance: Optional[ResearchWorkspace] = None


def get_research_workspace() -> ResearchWorkspace:
    """Returns the singleton ResearchWorkspace instance."""
    global _workspace_instance
    if _workspace_instance is None:
        _workspace_instance = ResearchWorkspace()
    return _workspace_instance
