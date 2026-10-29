"""
Autonomous Self-Healing OS Engine & Watchdog for NOVA OS.
Monitors memory pressure, clears stale cache locks, performs garbage collection,
and auto-trims process working sets to prevent stuttering on 4 GB RAM machines.
"""

import os
import gc
import psutil
from pathlib import Path
from typing import Dict, Any

from nova.config import DATA_DIR, DB_PATH
from nova.database import purge_transient_cache
from nova.memory_optimizer import flush_quantum_memory

class AutoRepairMatrix:
    """Self-healing watchdog matrix."""

    RAM_THRESHOLD_PERCENT = 85.0

    @classmethod
    def run_diagnostic_check(cls) -> Dict[str, Any]:
        """Runs comprehensive system health check and applies repairs if needed."""
        repairs_performed = []

        # 1. RAM pressure check
        mem = psutil.virtual_memory()
        if mem.percent >= cls.RAM_THRESHOLD_PERCENT:
            flush_quantum_memory(include_child_processes=True)
            gc.collect()
            repairs_performed.append(f"Trimmed process working set (RAM was at {mem.percent:.1f}%)")

        # 2. Stale database journals
        wal_file = DB_PATH.with_suffix(".db-wal")
        if wal_file.exists() and wal_file.stat().st_size > 10 * 1024 * 1024:
            try:
                import sqlite3
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.close()
                repairs_performed.append("Truncated large SQLite WAL journal")
            except Exception:
                pass

        # 3. Purge expired cache entries
        purged = purge_transient_cache()
        if isinstance(purged, dict) and purged.get("success"):
            repairs_performed.append(f"Purged transient cache buffers")
        elif isinstance(purged, int) and purged > 0:
            repairs_performed.append(f"Cleaned {purged} transient cache records")

        return {
            "status": "HEALTHY" if not repairs_performed else "AUTO_REPAIRED",
            "ram_percent": mem.percent,
            "repairs": repairs_performed,
            "available_mb": round(mem.available / (1024 * 1024), 1)
        }
