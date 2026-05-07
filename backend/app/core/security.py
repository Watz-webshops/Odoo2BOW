import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_api_token() -> str:
    return "sk_live_" + secrets.token_urlsafe(32)


def create_access_token(
    subject: str,
    role: str = "admin",
    org_id: str | None = None,
) -> str:
    """role = 'admin' | 'user'. Voor 'user' is org_id verplicht."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict = {"sub": subject, "exp": expire, "role": role}
    if org_id:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")


def create_refresh_token(subject: str, role: str = "admin") -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": subject, "exp": expire, "role": role, "type": "refresh"},
        settings.admin_jwt_secret,
        algorithm="HS256",
    )


def generate_password() -> str:
    """Veilig random wachtwoord (12 tekens, URL-safe)."""
    return secrets.token_urlsafe(9)  # 12 chars na base64


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.admin_jwt_secret, algorithms=["HS256"])
    except JWTError as e:
        raise ValueError("Invalid token") from e
