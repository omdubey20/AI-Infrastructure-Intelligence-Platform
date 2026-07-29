"""
Credential Encryption Service
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
to encrypt SSH passwords, SSH private keys, and WHM tokens before DB storage.
"""
import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

FALLBACK_KEY = b"lh_hTe9jCBEwRaR-FpbpZ5MauGEJNw9KoAD6jZZSjIw="


def _get_fernet() -> Fernet:
    """Get Fernet key from environment or fallback."""
    key = os.getenv("FERNET_KEY")
    if key:
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            pass
    return Fernet(FALLBACK_KEY)


_fernet: Fernet = None


def _fernet_instance() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


def encrypt_credential(value: str) -> str:
    """Encrypt a credential string. Returns base64-encoded ciphertext."""
    if not value:
        return value
    try:
        f = _fernet_instance()
        return f.encrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return value


def decrypt_credential(value: str) -> str:
    """Decrypt a Fernet-encrypted credential. Returns plaintext."""
    if not value:
        return value
    try:
        f = _fernet_instance()
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback to secondary Fernet instance if key was rotated
        try:
            f_fallback = Fernet(FALLBACK_KEY)
            return f_fallback.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            # If decryption fails, value is returned as-is (plaintext)
            return value


def is_encrypted(value: str) -> bool:
    """Check if a value looks like a Fernet token."""
    if not value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "==")
        return decoded[:1] == b'\x80'
    except Exception:
        return False
