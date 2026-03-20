"""
Credential / Secret Manager — encrypted local vault using Fernet symmetric
encryption (cryptography library). Falls back to base64 obfuscation if
cryptography is not installed (not secure, but at least not plaintext).

Vault stored at: data/vault.enc
Master key derived from user passphrase via PBKDF2-HMAC-SHA256.
Key salt stored at: data/vault.salt (NOT secret, used for derivation only)

Usage:
    vault = CredentialManager()
    vault.unlock("my_passphrase")
    vault.set("openai_key", "sk-...")
    key = vault.get("openai_key")
    vault.lock()
"""

from __future__ import annotations
import base64
import json
import os
import hashlib
from pathlib import Path
from typing import Optional


_VAULT_FILE = Path("data/vault.enc")
_SALT_FILE = Path("data/vault.salt")


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from a passphrase using PBKDF2."""
    dk = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000)
    return base64.urlsafe_b64encode(dk)


class CredentialManager:
    """Encrypted key-value credential vault."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._unlocked: bool = False
        self._key: Optional[bytes] = None
        _VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def unlock(self, passphrase: str) -> bool:
        """
        Unlock the vault with the given passphrase.
        If no vault exists, creates a new empty one.
        Returns True on success.
        """
        try:
            salt = self._get_or_create_salt()
            self._key = _derive_key(passphrase, salt)

            if _VAULT_FILE.exists():
                encrypted = _VAULT_FILE.read_bytes()
                plaintext = self._decrypt(encrypted)
                self._data = json.loads(plaintext)
            else:
                self._data = {}
                self._save()

            self._unlocked = True
            return True
        except Exception as e:
            self._unlocked = False
            self._key = None
            raise ValueError(f"Failed to unlock vault: {e}") from e

    def lock(self) -> None:
        """Lock the vault and clear in-memory secrets."""
        if self._unlocked:
            self._save()
        self._data = {}
        self._key = None
        self._unlocked = False

    def set(self, name: str, value: str, category: str = "general") -> None:
        """Store a secret. name should be descriptive, e.g. 'openai_api_key'."""
        self._require_unlocked()
        self._data[name] = json.dumps({"value": value, "category": category})
        self._save()

    def get(self, name: str) -> Optional[str]:
        """Retrieve a secret by name. Returns None if not found."""
        self._require_unlocked()
        raw = self._data.get(name)
        if raw is None:
            return None
        try:
            return json.loads(raw)["value"]
        except Exception:
            return raw  # legacy plain string

    def delete(self, name: str) -> bool:
        """Delete a secret. Returns True if it existed."""
        self._require_unlocked()
        if name in self._data:
            del self._data[name]
            self._save()
            return True
        return False

    def list_names(self, category: Optional[str] = None) -> list[str]:
        """List stored credential names (not values)."""
        self._require_unlocked()
        result = []
        for name, raw in self._data.items():
            if category is None:
                result.append(name)
            else:
                try:
                    entry = json.loads(raw)
                    if entry.get("category") == category:
                        result.append(name)
                except Exception:
                    result.append(name)
        return sorted(result)

    def get_all(self) -> dict[str, str]:
        """Return all secrets as {name: value} dict. Use carefully."""
        self._require_unlocked()
        result = {}
        for name, raw in self._data.items():
            try:
                result[name] = json.loads(raw)["value"]
            except Exception:
                result[name] = raw
        return result

    def change_passphrase(self, old: str, new: str) -> None:
        """Re-encrypt the vault with a new passphrase."""
        if not self._unlocked:
            self.unlock(old)
        data_snapshot = dict(self._data)
        # Generate new salt
        new_salt = os.urandom(32)
        _SALT_FILE.write_bytes(new_salt)
        self._key = _derive_key(new, new_salt)
        self._data = data_snapshot
        self._save()

    def inject_to_env(self, prefix: str = "") -> None:
        """
        Inject all stored credentials into os.environ.
        Useful so tools can read them via os.getenv().
        Names are uppercased with optional prefix.
        """
        self._require_unlocked()
        for name, raw in self._data.items():
            try:
                value = json.loads(raw)["value"]
            except Exception:
                value = raw
            env_key = (prefix + name).upper().replace("-", "_").replace(" ", "_")
            os.environ[env_key] = value

    def get_env_compatible(self, name: str) -> Optional[str]:
        """
        Get credential with fallback to os.environ.
        Tries vault first, then env var (uppercase name).
        """
        if self._unlocked:
            val = self.get(name)
            if val:
                return val
        return os.environ.get(name.upper().replace("-", "_"))

    # ── Internal ───────────────────────────────────────────────────────────────

    def _require_unlocked(self) -> None:
        if not self._unlocked:
            raise RuntimeError("Vault is locked. Call unlock(passphrase) first.")

    def _get_or_create_salt(self) -> bytes:
        if _SALT_FILE.exists():
            return _SALT_FILE.read_bytes()
        salt = os.urandom(32)
        _SALT_FILE.write_bytes(salt)
        return salt

    def _encrypt(self, plaintext: str) -> bytes:
        # SECURITY: cryptography is a hard requirement — no insecure fallback
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            raise RuntimeError(
                "cryptography package is required for the vault. "                "Run: pip install cryptography"
            )
        f = Fernet(self._key)
        return f.encrypt(plaintext.encode())

    def _decrypt(self, data: bytes) -> str:
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            raise RuntimeError(
                "cryptography package is required for the vault. "                "Run: pip install cryptography"
            )
        try:
            f = Fernet(self._key)
            return f.decrypt(data).decode()
        except Exception:
            raise ValueError("Failed to decrypt vault — wrong passphrase or corrupted vault.")

    def _save(self) -> None:
        if self._key is None:
            return
        plaintext = json.dumps(self._data)
        encrypted = self._encrypt(plaintext)
        _VAULT_FILE.write_bytes(encrypted)


# ── Singleton for use across the system ─────────────────────────────────────

_vault_instance: Optional[CredentialManager] = None


def get_vault() -> CredentialManager:
    """Get the global vault instance."""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = CredentialManager()
    return _vault_instance


def auto_unlock_from_env() -> bool:
    """
    Auto-unlock vault using AI_HUMAN_VAULT_PASS environment variable.
    This allows headless operation without interactive passphrase entry.
    """
    passphrase = os.environ.get("AI_HUMAN_VAULT_PASS")
    if not passphrase:
        return False
    try:
        get_vault().unlock(passphrase)
        return True
    except Exception:
        return False
