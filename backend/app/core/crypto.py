"""
Fernet symmetric encryption voor secrets at rest (Odoo API keys).

Vereist: ENCRYPTION_KEY env var (32-byte url-safe base64).
Genereer met:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY niet ingesteld. Genereer met: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plain: str) -> str:
    """Versleutel een string. Returnt base64 ciphertext."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(cipher: str) -> str:
    """Ontsleutel een ciphertext."""
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Kan niet ontsleutelen — verkeerde of beschadigde key") from e


def generate_webhook_secret() -> str:
    """Genereert een random secret voor webhook HMAC (32 hex chars)."""
    return secrets.token_hex(32)
