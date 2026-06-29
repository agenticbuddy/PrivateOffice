"""Password hashing, random tokens and signed WOPI tokens."""
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()
_ph = PasswordHasher()
_signer = URLSafeTimedSerializer(settings.secret_key, salt="wopi-token")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _ph.verify(password_hash, password)
    except Argon2Error:  # mismatch, or a corrupt/foreign hash — never 500 the login
        return False


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sign_wopi_token(payload: dict) -> str:
    """Sign a WOPI access token: (user_id, node_id, can_write)."""
    return _signer.dumps(payload)


def verify_wopi_token(token: str, max_age: int | None = None) -> dict | None:
    try:
        return _signer.loads(token, max_age=max_age or settings.wopi_token_ttl)
    except BadSignature:
        return None
