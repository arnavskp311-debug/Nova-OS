"""
NOVA OS Download Security & Quarantine Subsystem.
Validates downloaded files against high-risk executable signatures,
calculates SHA-256 cryptographic hashes, detects PE/MZ binary headers,
and isolates suspicious payloads into a dedicated quarantine sandbox.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from nova.config import DATA_DIR, PROHIBITED_EXTENSIONS
from nova.database import log_command

logger = logging.getLogger("nova.download_security")

QUARANTINE_DIR = DATA_DIR / "quarantine"
QUARANTINE_FILES = QUARANTINE_DIR / "files"
QUARANTINE_MANIFEST = QUARANTINE_DIR / "manifest.json"

# Dangerous extensions subject to immediate security review or quarantine
DANGEROUS_EXTENSIONS = PROHIBITED_EXTENSIONS.union({
    ".jar", ".vbe", ".hta", ".cpl", ".wsf", ".wsh", ".msc", ".gadget", ".iso", ".img"
})

# Known malicious or executable binary magic bytes
BINARY_MAGIC_SIGNATURES = {
    b"MZ": "Windows DOS/PE Executable (MZ Header)",
    b"\x7fELF": "Linux ELF Executable Binary",
    b"\xca\xfe\xba\xbe": "Java Class / Mach-O Universal Binary",
    b"PK\x03\x04": "ZIP / Jar Compressed Archive",
    b"Rar!\x1a\x07": "RAR Archive",
    b"\x1f\x8b": "GZIP Compressed Stream"
}


class DownloadValidator:
    """
    Scans, verifies, and quarantines untrusted downloaded files.
    Calculates cryptographic SHA-256 hashes and inspects magic bytes.
    """

    @classmethod
    def _init_storage(cls):
        QUARANTINE_FILES.mkdir(parents=True, exist_ok=True)
        if not QUARANTINE_MANIFEST.exists():
            with open(QUARANTINE_MANIFEST, "w", encoding="utf-8") as f:
                json.dump([], f)

    @classmethod
    def calculate_sha256(cls, file_path: Path) -> str:
        """Calculates cryptographic SHA-256 checksum of a file."""
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception as e:
            logger.error(f"SHA-256 computation error on {file_path}: {e}")
            return "error_reading_file"

    @classmethod
    def inspect_file(cls, file_path: Path) -> Dict[str, Any]:
        """
        Inspects a file for dangerous extensions and binary magic signatures.
        Detects executables masked with harmless extensions (e.g. payload.exe -> image.jpg).
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return {"is_safe": False, "reason": "File does not exist or is inaccessible."}

        ext = p.suffix.lower()
        size_bytes = p.stat().st_size
        sha256 = cls.calculate_sha256(p)

        # 1. Extension inspection
        is_risky_ext = ext in DANGEROUS_EXTENSIONS

        # 2. Inspect magic bytes header
        header_desc = "Unknown"
        is_masked_binary = False
        try:
            with open(p, "rb") as f:
                magic_bytes = f.read(4)
                for sig, desc in BINARY_MAGIC_SIGNATURES.items():
                    if magic_bytes.startswith(sig):
                        header_desc = desc
                        if sig == b"MZ" and ext not in [".exe", ".dll", ".sys"]:
                            is_masked_binary = True
                        break
        except Exception:
            pass

        if is_masked_binary:
            return {
                "is_safe": False,
                "is_executable": True,
                "is_masked": True,
                "reason": f"CRITICAL: Executable MZ binary disguised with '{ext}' extension.",
                "extension": ext,
                "header": header_desc,
                "size_bytes": size_bytes,
                "sha256": sha256
            }

        if is_risky_ext:
            return {
                "is_safe": False,
                "is_executable": True,
                "is_masked": False,
                "reason": f"High-risk executable or script file extension: '{ext}'.",
                "extension": ext,
                "header": header_desc,
                "size_bytes": size_bytes,
                "sha256": sha256
            }

        return {
            "is_safe": True,
            "is_executable": False,
            "is_masked": False,
            "reason": "File verified safe. No prohibited binary or script signatures found.",
            "extension": ext,
            "header": header_desc,
            "size_bytes": size_bytes,
            "sha256": sha256
        }

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        cls._init_storage()
        try:
            with open(QUARANTINE_MANIFEST, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def _save_manifest(cls, data: List[Dict[str, Any]]):
        cls._init_storage()
        with open(QUARANTINE_MANIFEST, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def quarantine_file(cls, file_path: Path, source_url: str = "", reason: str = "") -> Optional[str]:
        """
        Moves a suspicious file into the quarantine vault and records its manifest.
        Returns the unique quarantine_id or None on failure.
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return None

        cls._init_storage()
        sha256 = cls.calculate_sha256(p)
        quarantine_id = f"quar_{int(time.time() * 1000)}"
        vault_filename = f"{quarantine_id}_{p.name}.quarantined"
        vault_target = QUARANTINE_FILES / vault_filename

        try:
            # Move file to quarantine
            os.replace(str(p), str(vault_target))

            entry = {
                "id": quarantine_id,
                "original_name": p.name,
                "original_path": str(p),
                "vault_file": str(vault_target),
                "source_url": source_url,
                "reason": reason or "High-risk executable file quarantined for Windows host safety.",
                "size_bytes": vault_target.stat().st_size,
                "sha256": sha256,
                "quarantined_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "QUARANTINED"
            }

            manifest = cls.get_manifest()
            manifest.append(entry)
            cls._save_manifest(manifest)

            # Log to SQLite security audit vault
            log_command(
                command=f"QUARANTINE: {p.name} (SHA-256: {sha256[:16]}...)",
                risk_level="HIGH",
                status="QUARANTINED",
                output=f"File isolated to {vault_target}. Reason: {entry['reason']}",
                approved=False
            )

            logger.warning(f"File quarantined: {p.name} -> {vault_target}")
            return quarantine_id
        except Exception as e:
            logger.error(f"Failed to quarantine file {p}: {e}")
            return None

    @classmethod
    def release_file(cls, quarantine_id: str, dest_dir: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Releases a file from quarantine to the destination directory upon explicit user authorization.
        """
        manifest = cls.get_manifest()
        entry = next((item for item in manifest if item["id"] == quarantine_id), None)
        if not entry:
            return False, "Quarantine record not found."

        vault_path = Path(entry["vault_file"])
        if not vault_path.exists():
            return False, "Quarantined file payload missing from vault."

        target_dir = dest_dir or Path(entry["original_path"]).parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / entry["original_name"]

        try:
            os.replace(str(vault_path), str(target_path))
            manifest = [item for item in manifest if item["id"] != quarantine_id]
            cls._save_manifest(manifest)

            # Log release to security audit vault
            log_command(
                command=f"RELEASE QUARANTINE: {entry['original_name']}",
                risk_level="HIGH",
                status="RELEASED",
                output=f"Restored to {target_path} upon user explicit authorization.",
                approved=True
            )
            return True, f"File successfully released to:\n{target_path}"
        except Exception as e:
            return False, f"Failed to release file: {e}"

    @classmethod
    def delete_quarantined_file(cls, quarantine_id: str) -> Tuple[bool, str]:
        """Permanently shreds/deletes a quarantined file."""
        manifest = cls.get_manifest()
        entry = next((item for item in manifest if item["id"] == quarantine_id), None)
        if not entry:
            return False, "Quarantine record not found."

        vault_path = Path(entry["vault_file"])
        try:
            if vault_path.exists():
                vault_path.unlink()
            manifest = [item for item in manifest if item["id"] != quarantine_id]
            cls._save_manifest(manifest)

            log_command(
                command=f"DELETE QUARANTINED: {entry['original_name']}",
                risk_level="SAFE",
                status="DELETED",
                output="Quarantined file purged.",
                approved=True
            )
            return True, f"Quarantined file '{entry['original_name']}' permanently purged."
        except Exception as e:
            return False, f"Failed to purge quarantined file: {e}"
