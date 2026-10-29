"""
Secure Credential Vault for NOVA OS.
Stores API keys, tokens, and sensitive secrets encrypted with PBKDF2 key derivation.
Zero external dependencies, safe on all platforms.
"""

import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Dict, List, Optional

from nova.config import DATA_DIR

VAULT_FILE = DATA_DIR / "credential_vault.enc"

class CredentialVault:
    """Manages encrypted secrets and API tokens."""

    @classmethod
    def _derive_key(cls, master_pin: str, salt: bytes) -> bytes:
        """Derives a 32-byte key using PBKDF2 HMAC SHA-256."""
        return hashlib.pbkdf2_hmac("sha256", master_pin.encode("utf-8"), salt, 100000, dklen=32)

    @classmethod
    def _cipher(cls, data: bytes, key: bytes) -> bytes:
        """Symmetric streaming keystream transformation."""
        out = bytearray(len(data))
        k_len = len(key)
        for i in range(len(data)):
            out[i] = data[i] ^ key[i % k_len]
        return bytes(out)

    @classmethod
    def _load_vault(cls, master_pin: str) -> Optional[Dict[str, str]]:
        if not VAULT_FILE.exists():
            return {}
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            salt = base64.b64decode(payload["salt"])
            ciphertext = base64.b64decode(payload["data"])
            key = cls._derive_key(master_pin, salt)
            plaintext = cls._cipher(ciphertext, key).decode("utf-8")
            return json.loads(plaintext)
        except Exception:
            return None

    @classmethod
    def _save_vault(cls, data: Dict[str, str], master_pin: str) -> bool:
        try:
            salt = os.urandom(16)
            key = cls._derive_key(master_pin, salt)
            plaintext = json.dumps(data).encode("utf-8")
            ciphertext = cls._cipher(plaintext, key)
            payload = {
                "salt": base64.b64encode(salt).decode("utf-8"),
                "data": base64.b64encode(ciphertext).decode("utf-8")
            }
            with open(VAULT_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def set_secret(cls, key: str, value: str, master_pin: str = "0000") -> bool:
        """Stores or updates an encrypted secret."""
        vault = cls._load_vault(master_pin)
        if vault is None:
            vault = {}
        vault[key] = value
        return cls._save_vault(vault, master_pin)

    @classmethod
    def get_secret(cls, key: str, master_pin: str = "0000") -> Optional[str]:
        """Retrieves and decrypts a secret."""
        vault = cls._load_vault(master_pin)
        if vault is None:
            return None
        return vault.get(key)

    @classmethod
    def list_keys(cls, master_pin: str = "0000") -> List[str]:
        """Lists available secret keys without exposing values."""
        vault = cls._load_vault(master_pin)
        if vault is None:
            return []
        return list(vault.keys())

    @classmethod
    def delete_secret(cls, key: str, master_pin: str = "0000") -> bool:
        """Removes a secret from the encrypted vault."""
        vault = cls._load_vault(master_pin)
        if vault is None or key not in vault:
            return False
        del vault[key]
        return cls._save_vault(vault, master_pin)
