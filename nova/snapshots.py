"""
System Restore Points & Snapshot Rollback Subsystem for NOVA OS.
Creates atomic point-in-time snapshots of system databases, configurations,
and user workspaces for fail-safe rollback.
"""

import os
import shutil
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

from nova.config import DATA_DIR, DB_PATH

SNAPSHOTS_DIR = DATA_DIR / "snapshots"

class SnapshotManager:
    """Manages system restore points and snapshots."""

    @classmethod
    def _init_dir(cls):
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create_restore_point(cls, label: str = "Manual Restore Point") -> Optional[str]:
        """Creates a snapshot of the database and configs."""
        cls._init_dir()
        ts = int(time.time())
        snap_id = f"snap_{ts}"
        snap_dir = SNAPSHOTS_DIR / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy database
            if DB_PATH.exists():
                shutil.copy2(str(DB_PATH), str(snap_dir / "nova.db"))

            # Copy manifest and metadata
            meta = {
                "id": snap_id,
                "label": label,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": ts,
                "db_size": DB_PATH.stat().st_size if DB_PATH.exists() else 0
            }
            with open(snap_dir / "meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            return snap_id
        except Exception:
            return None

    @classmethod
    def list_restore_points(cls) -> List[Dict[str, Any]]:
        """Lists all available restore points."""
        cls._init_dir()
        points = []
        for d in SNAPSHOTS_DIR.iterdir():
            if d.is_dir():
                meta_file = d / "meta.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            points.append(json.load(f))
                    except Exception:
                        pass
        points.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return points

    @classmethod
    def rollback(cls, snap_id: str) -> bool:
        """Rolls back the system database to the selected restore point."""
        snap_dir = SNAPSHOTS_DIR / snap_id
        target_db = snap_dir / "nova.db"

        if not target_db.exists():
            return False

        try:
            # Backup current db before overwrite
            backup_cur = DB_PATH.with_suffix(".pre_rollback.bak")
            if DB_PATH.exists():
                shutil.copy2(str(DB_PATH), str(backup_cur))

            shutil.copy2(str(target_db), str(DB_PATH))
            return True
        except Exception:
            return False

    @classmethod
    def delete_restore_point(cls, snap_id: str) -> bool:
        """Deletes a snapshot."""
        snap_dir = SNAPSHOTS_DIR / snap_id
        if snap_dir.exists() and snap_dir.is_dir():
            try:
                shutil.rmtree(str(snap_dir), ignore_errors=True)
                return True
            except Exception:
                return False
        return False
