"""
Credential Encryption Service
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
to encrypt SSH passwords, SSH private keys, and WHM tokens before DB storage.

IMPORTANT: Set FERNET_KEY in your .env file.
Generate a new key with:
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet key from environment variable. Raises if not configured."""
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError(
            "FERNET_KEY environment variable is not set. "
            "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise RuntimeError(f"FERNET_KEY is invalid: {e}") from e


_fernet: Fernet = None


def _fernet_instance() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


def encrypt_credential(value: str) -> str:
    """Encrypt a credential string. Returns Fernet ciphertext."""
    if not value:
        return value
    try:
        f = _fernet_instance()
        return f.encrypt(value.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Credential encryption failed: {e}")
        return value


def decrypt_credential(value: str) -> str:
    """Decrypt a Fernet-encrypted credential. Returns plaintext."""
    if not value:
        return value
    try:
        f = _fernet_instance()
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception as e:
        # If decryption fails, the value may already be plaintext (legacy)
        logger.debug(f"Credential decryption notice (may be plaintext): {e}")
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
