"""
SQLite database manager for NOVA OS.
Stores chat history, notes, application settings, and command logs locally.
"""

import os
import sqlite3
import json
import logging
import threading
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from nova.config import DB_PATH, BACKUPS_DIR, BROWSER_PROFILE_DIR, LOGS_DIR, DATA_DIR

logger = logging.getLogger("nova.database")

_local_storage = threading.local()

CURRENT_SCHEMA_VERSION = 3

def get_connection() -> sqlite3.Connection:
    """Returns a fast, thread-local pooled SQLite connection with WAL mode enabled."""
    conn = getattr(_local_storage, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -32000")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 268435456")
        _local_storage.conn = conn
    return conn

def close_connection():
    """Closes thread-local connection if open."""
    conn = getattr(_local_storage, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local_storage.conn = None

def init_db():
    """Initializes tables, high-performance indexes, and executes migrations."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Schema Migrations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)

        # Chat sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chat messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)

        # Notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Command safety logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                output TEXT,
                approved INTEGER DEFAULT 0,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Browser Bookmarks (Isolated from Chrome, support explicit tagging & reversal)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                folder TEXT DEFAULT 'Bookmarks',
                imported_from TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Browser History (Isolated, support safe import & reversal)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_from TEXT DEFAULT ''
            )
        """)

        # Browser Downloads Table (Schema v2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                url TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                status TEXT DEFAULT 'COMPLETED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Reminders Table (Schema v3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TIMESTAMP NOT NULL,
                priority TEXT DEFAULT 'NORMAL',
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clipboard History Table (Schema v3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Performance Indexes for sub-millisecond query execution
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, id ASC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_history_url ON browser_history(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_history_visit ON browser_history(visit_time DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_bookmarks_url ON browser_bookmarks(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_bookmarks_folder ON browser_bookmarks(folder)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_downloads_created ON browser_downloads(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_at ASC, is_completed ASC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_created ON clipboard_history(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_logs_time ON command_logs(executed_at DESC)")

        # Record migration records if not present
        cursor.execute("INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (1, 'Baseline schema: chats, notes, settings, logs, browser history & bookmarks')")
        cursor.execute("INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (2, 'Schema v2: browser_downloads tracking and composite indexes')")
        cursor.execute("INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (3, 'Schema v3: desktop essentials (reminders, clipboard history)')")

        conn.commit()
    logger.info(f"Database initialized at {DB_PATH} (Schema v{CURRENT_SCHEMA_VERSION})")

def check_database_integrity() -> Tuple[bool, str, int]:
    """Runs PRAGMA integrity_check and returns (is_healthy, status_message, current_version)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            res = cursor.fetchone()
            check_result = res[0] if res else "Unknown"
            
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            v_row = cursor.fetchone()
            version = v_row[0] if v_row and v_row[0] else 1

            if check_result == "ok":
                return True, "Database integrity verification passed: OK", version
            else:
                return False, f"Integrity verification issue: {check_result}", version
    except Exception as e:
        return False, f"Integrity check failed: {str(e)}", 0

def create_database_backup(dest_dir: Optional[Path] = None) -> Tuple[bool, str, Optional[Path]]:
    """
    Safely creates a consistent online snapshot backup of the SQLite database.
    Uses sqlite3 online backup API to prevent corruption or WAL lock contention.
    """
    try:
        target_dir = dest_dir or BACKUPS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nova_backup_{timestamp}.db"
        backup_path = target_dir / backup_filename

        # Online SQLite backup
        with get_connection() as source_conn:
            with sqlite3.connect(backup_path) as dest_conn:
                source_conn.backup(dest_conn, pages=100)

        size_kb = round(backup_path.stat().st_size / 1024, 1)
        msg = f"Backup created successfully: {backup_filename} ({size_kb} KB)"
        logger.info(msg)
        return True, msg, backup_path
    except Exception as e:
        err = f"Failed to create database backup: {str(e)}"
        logger.error(err)
        return False, err, None

def restore_database_backup(backup_path: Path) -> Tuple[bool, str]:
    """
    Safely restores the database from a backup file after verifying its integrity.
    Uses SQLite's online backup API to stream pages directly into the live database.
    """
    try:
        p = Path(backup_path)
        if not p.is_file():
            return False, f"Backup file not found at: {p}"

        # Verify integrity of target backup file first
        with sqlite3.connect(p) as test_conn:
            cur = test_conn.cursor()
            cur.execute("PRAGMA integrity_check")
            chk = cur.fetchone()
            if not chk or chk[0] != "ok":
                return False, f"Backup file integrity validation failed: {chk}"

        # Stream verified backup into the live database
        with sqlite3.connect(p) as backup_conn:
            with get_connection() as live_conn:
                backup_conn.backup(live_conn, pages=100)

        # Re-initialize to verify and apply any migrations
        init_db()
        return True, f"Successfully restored database from: {p.name}"
    except Exception as e:
        err = f"Failed to restore backup: {str(e)}"
        logger.error(err)
        return False, err

# ----------------- Chat Session & Message Operations -----------------

def create_chat_session(title: str = "New Transmission") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_sessions (title) VALUES (?)", (title,))
        conn.commit()
        return cursor.lastrowid

def get_chat_sessions() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def update_chat_session_title(session_id: int, title: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (title, session_id))
        conn.commit()

def delete_chat_session(session_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()

def add_chat_message(session_id: int, role: str, content: str, model: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, model) VALUES (?, ?, ?, ?)",
            (session_id, role, content, model)
        )
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        conn.commit()

def get_chat_messages(session_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

# ----------------- Notes Operations -----------------

def create_note(title: str, content: str, tags: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, tags)
        )
        conn.commit()
        return cursor.lastrowid

def get_notes() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def update_note(note_id: int, title: str, content: str, tags: str = ""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, content, tags, note_id)
        )
        conn.commit()

def delete_note(note_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()

# ----------------- Settings Operations -----------------

def get_setting(key: str, default: Any = None) -> Any:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return row["value"]
        return default

def set_setting(key: str, value: Any):
    with get_connection() as conn:
        cursor = conn.cursor()
        val_str = json.dumps(value)
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, val_str)
        )
        conn.commit()

# ----------------- Command & Security Logs -----------------

def log_command(command: str, risk_level: str, status: str, output: str = "", approved: bool = False):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO command_logs (command, risk_level, status, output, approved) VALUES (?, ?, ?, ?, ?)",
            (command, risk_level, status, output[:2000], 1 if approved else 0)
        )
        conn.commit()

def get_recent_command_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM command_logs ORDER BY executed_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

# ----------------- NOVA Browser Operations (Safe & Isolated) -----------------

def add_browser_bookmark(title: str, url: str, folder: str = "Bookmarks", imported_from: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO browser_bookmarks (title, url, folder, imported_from) VALUES (?, ?, ?, ?)",
            (title.strip() or url, url.strip(), folder.strip() or "Bookmarks", imported_from.strip())
        )
        conn.commit()
        return cursor.lastrowid

def add_browser_bookmarks_batch(entries: List[Tuple[str, str, str, str]]) -> int:
    """High-performance batched bookmark insertion within a single atomic transaction."""
    if not entries:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        cursor.executemany(
            "INSERT INTO browser_bookmarks (title, url, folder, imported_from) VALUES (?, ?, ?, ?)",
            entries
        )
        conn.commit()
        return len(entries)

def get_browser_bookmarks(search_query: str = "") -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if search_query.strip():
            pattern = f"%{search_query.strip()}%"
            cursor.execute(
                "SELECT * FROM browser_bookmarks WHERE title LIKE ? OR url LIKE ? OR folder LIKE ? ORDER BY created_at DESC",
                (pattern, pattern, pattern)
            )
        else:
            cursor.execute("SELECT * FROM browser_bookmarks ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def delete_browser_bookmark(bookmark_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM browser_bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()

def delete_imported_bookmarks(source_prefix: str = "Chrome") -> int:
    """Safely and reversibly purges bookmarks imported from Chrome without touching native bookmarks."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM browser_bookmarks WHERE imported_from LIKE ?", (f"%{source_prefix}%",))
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

def add_browser_history(title: str, url: str, imported_from: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO browser_history (title, url, imported_from) VALUES (?, ?, ?)",
            (title.strip() or url, url.strip(), imported_from.strip())
        )
        conn.commit()
        return cursor.lastrowid

def add_browser_history_batch(entries: List[Tuple[str, str, str]]) -> int:
    """High-performance batched history insertion within a single atomic transaction."""
    if not entries:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        cursor.executemany(
            "INSERT INTO browser_history (title, url, imported_from) VALUES (?, ?, ?)",
            entries
        )
        conn.commit()
        return len(entries)

def get_browser_history(search_query: str = "", limit: int = 150) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if search_query.strip():
            pattern = f"%{search_query.strip()}%"
            cursor.execute(
                "SELECT * FROM browser_history WHERE title LIKE ? OR url LIKE ? ORDER BY id DESC LIMIT ?",
                (pattern, pattern, limit)
            )
        else:
            cursor.execute("SELECT * FROM browser_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def clear_browser_history(only_imported: bool = False) -> int:
    """Clears browsing history. Can selectively target only imported Chrome entries for clean reversal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if only_imported:
            cursor.execute("DELETE FROM browser_history WHERE imported_from != ''")
        else:
            cursor.execute("DELETE FROM browser_history")
        deleted = cursor.rowcount
        conn.commit()
        return deleted

# ----------------- NOVA Browser Downloads Operations -----------------

def add_browser_download(file_name: str, file_path: str, url: str, file_size: int = 0, status: str = "COMPLETED") -> int:
    """Records a browser download item into persistent database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO browser_downloads (file_name, file_path, url, file_size, status) VALUES (?, ?, ?, ?, ?)",
            (file_name.strip(), file_path.strip(), url.strip(), file_size, status.strip())
        )
        conn.commit()
        return cursor.lastrowid

def get_browser_downloads(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent downloads ordered by newest first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM browser_downloads ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def clear_browser_downloads() -> int:
    """Clears download history records without deleting downloaded files on disk."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM browser_downloads")
        deleted = cursor.rowcount
        conn.commit()
        return deleted

# ----------------- Reminders & Scheduler Operations -----------------

def create_reminder(title: str, due_at: str, priority: str = "NORMAL") -> int:
    """Creates a reminder with due date/time (ISO format YYYY-MM-DD HH:MM)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (title, due_at, priority) VALUES (?, ?, ?)",
            (title.strip(), due_at.strip(), priority.upper())
        )
        conn.commit()
        return cursor.lastrowid

def get_reminders(include_completed: bool = False) -> List[Dict[str, Any]]:
    """Retrieves active (or all) reminders ordered by urgency."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if include_completed:
            cursor.execute("SELECT * FROM reminders ORDER BY is_completed ASC, due_at ASC")
        else:
            cursor.execute("SELECT * FROM reminders WHERE is_completed = 0 ORDER BY due_at ASC")
        return [dict(row) for row in cursor.fetchall()]

def get_due_reminders() -> List[Dict[str, Any]]:
    """Retrieves overdue or currently due active reminders."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM reminders WHERE is_completed = 0 AND due_at <= ? ORDER BY due_at ASC",
            (now_str,)
        )
        return [dict(row) for row in cursor.fetchall()]

def complete_reminder(reminder_id: int):
    """Marks a reminder as completed."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
        conn.commit()

def delete_reminder(reminder_id: int):
    """Deletes a reminder permanently."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()

# ----------------- Clipboard History Operations -----------------

def add_clipboard_entry(content: str) -> bool:
    """Adds a text snippet into clipboard history (max 30 items, deduplicated)."""
    text = content.strip()
    if not text or len(text) > 10000:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        # Insert or replace to refresh timestamp
        cursor.execute(
            "INSERT INTO clipboard_history (content, created_at) VALUES (?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(content) DO UPDATE SET created_at = CURRENT_TIMESTAMP",
            (text,)
        )
        # Purge beyond 30 items
        cursor.execute("""
            DELETE FROM clipboard_history WHERE id NOT IN (
                SELECT id FROM clipboard_history ORDER BY created_at DESC LIMIT 30
            )
        """)
        conn.commit()
        return True

def get_clipboard_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves recent clipboard history items."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clipboard_history ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def clear_clipboard_history() -> int:
    """Clears all stored clipboard history snippets."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clipboard_history")
        deleted = cursor.rowcount
        conn.commit()
        return deleted

# ----------------- Storage & Cache Management -----------------

def purge_transient_cache() -> Dict[str, Any]:
    """
    Safely purges transient browser cache, temporary logs, and compacts database
    to preserve storage on 256 GB SSD and conserve memory on 4 GB RAM.
    """
    freed_bytes = 0
    purged_items = []

    # 1. Clear WebEngine cache directory
    cache_dir = BROWSER_PROFILE_DIR / "cache"
    if cache_dir.exists():
        for root, dirs, files in os.walk(cache_dir, topdown=False):
            for name in files:
                f_path = Path(root) / name
                try:
                    freed_bytes += f_path.stat().st_size
                    f_path.unlink(missing_ok=True)
                except Exception:
                    pass
            for d in dirs:
                try:
                    (Path(root) / d).rmdir()
                except Exception:
                    pass
        purged_items.append("Browser disk cache")

    # 2. Clear Transient Audio Cache (Kokoro & Piper)
    audio_cache_dir = DATA_DIR / "audio_cache"
    if audio_cache_dir.exists():
        for root, dirs, files in os.walk(audio_cache_dir, topdown=False):
            for name in files:
                f_path = Path(root) / name
                try:
                    freed_bytes += f_path.stat().st_size
                    f_path.unlink(missing_ok=True)
                except Exception:
                    pass
            for d in dirs:
                try:
                    (Path(root) / d).rmdir()
                except Exception:
                    pass
        purged_items.append("Voice audio cache")

    # 3. Compact database
    try:
        with get_connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("VACUUM")
        purged_items.append("SQLite WAL buffers & vacuumed pages")
    except Exception:
        pass

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    return {
        "success": True,
        "freed_mb": freed_mb,
        "purged_items": purged_items
    }



