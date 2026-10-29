"""
Global File Search & Indexing Engine for NOVA OS.
Scans project workspaces and user directories for instant filename,
extension, and keyword lookups.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

from nova.config import BASE_DIR, DATA_DIR

class FileIndexer:
    """Fast directory search and indexer."""

    _cached_index: List[Dict[str, Any]] = []

    @classmethod
    def build_index(cls, search_root: Optional[Path] = None, max_files: int = 2000) -> int:
        """Indexes files in workspace root up to max_files."""
        root = search_root or BASE_DIR
        cls._cached_index.clear()

        count = 0
        skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}

        for dirpath, dirnames, filenames in os.walk(str(root)):
            # Prune skipped dirs
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]

            for fname in filenames:
                fpath = Path(dirpath) / fname
                try:
                    cls._cached_index.append({
                        "name": fname,
                        "path": str(fpath),
                        "extension": fpath.suffix.lower(),
                        "size": fpath.stat().st_size
                    })
                    count += 1
                    if count >= max_files:
                        return count
                except Exception:
                    pass

        return count

    @classmethod
    def search(cls, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Searches indexed files for substring match on filename or extension."""
        if not cls._cached_index:
            cls.build_index()

        q = query.strip().lower()
        if not q:
            return cls._cached_index[:limit]

        matches = []
        for item in cls._cached_index:
            if q in item["name"].lower():
                matches.append(item)
                if len(matches) >= limit:
                    break
        return matches
