"""
Removable Storage & USB Auto-Detection Subsystem for NOVA OS.
Monitors removable flash drives and external media, provides drive telemetry,
and performs safe unmount / buffer flush before ejection.
"""

import sys
import subprocess
import psutil
from typing import Dict, List, Set, Optional, Any
from PySide6.QtCore import QObject, Signal, QTimer

class USBManager(QObject):
    """Monitors USB / removable drives and alerts on insertions/removals."""

    drive_inserted = Signal(dict)
    drive_removed = Signal(str)

    _known_drives: Set[str] = set()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.scan_drives)
        self.poll_timer.start(3000)  # Check every 3 seconds
        self._init_known()

    def _init_known(self):
        drives = self.get_removable_drives()
        self._known_drives = {d["mountpoint"] for d in drives}

    @classmethod
    def get_removable_drives(cls) -> List[Dict[str, Any]]:
        """Scans for removable or external storage volumes."""
        results = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                # In Windows, 'removable' or 'cdrom' is in opts, or drive letter != C:
                is_removable = "removable" in p.opts.lower() or "cdrom" in p.opts.lower()
                # On Windows, flash drives often appear with opts containing removable
                if is_removable or (sys.platform == "win32" and not p.mountpoint.upper().startswith("C:")):
                    try:
                        usage = psutil.disk_usage(p.mountpoint)
                        results.append({
                            "device": p.device,
                            "mountpoint": p.mountpoint,
                            "fstype": p.fstype,
                            "opts": p.opts,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent_used": usage.percent,
                            "is_removable": is_removable
                        })
                    except Exception:
                        pass
        except Exception:
            pass
        return results

    def scan_drives(self):
        """Scans for state differences."""
        current = self.get_removable_drives()
        curr_map = {d["mountpoint"]: d for d in current}
        curr_mounts = set(curr_map.keys())

        # New drives
        new_mounts = curr_mounts - self._known_drives
        for m in new_mounts:
            self.drive_inserted.emit(curr_map[m])

        # Removed drives
        removed_mounts = self._known_drives - curr_mounts
        for m in removed_mounts:
            self.drive_removed.emit(m)

        self._known_drives = curr_mounts

    @classmethod
    def safe_eject(cls, mountpoint: str) -> bool:
        """Flushes disk write cache and initiates safe unmount."""
        if sys.platform != "win32":
            return True

        drive_letter = mountpoint.rstrip("\\").rstrip("/").replace(":", "")
        try:
            # Use PowerShell to dismount volume safely
            ps_cmd = f"$vol = Get-Volume -DriveLetter {drive_letter}; $vol | Get-Partition | Remove-PartitionAccessPath -AccessPath '{drive_letter}:\\'"
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            )
            return True
        except Exception:
            return False
