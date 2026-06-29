"""Authentication service: users, password login, sessions, magic links.

Pure data/business logic over an AsyncSession so it is unit-testable without HTTP.
"""
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import MagicLink, Session, User
from app.models import _now
from app.security import hash_password, random_token, verify_password
from app.util import as_aware, now

settings = get_settings()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    res = await db.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    locale: str = "en",
    is_admin: bool = False,
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        locale=locale,
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()
    return user


async def set_password(db: AsyncSession, user: User, password: str) -> None:
    user.password_hash = hash_password(password)
    await db.flush()


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ---- Sessions ----
async def create_session(db: AsyncSession, user: User) -> str:
    sid = random_token(32)
    db.add(
        Session(
            id=sid,
            user_id=user.id,
            expires_at=_now() + timedelta(seconds=settings.session_ttl),
        )
    )
    await db.flush()
    return sid


async def get_session_user(db: AsyncSession, sid: str | None) -> User | None:
    if not sid:
        return None
    sess = await db.get(Session, sid)
    if not sess or as_aware(sess.expires_at) <= now():
        return None
    user = await db.get(User, sess.user_id)
    if not user or not user.is_active:
        return None
    return user


async def delete_session(db: AsyncSession, sid: str | None) -> None:
    if not sid:
        return
    sess = await db.get(Session, sid)
    if sess:
        await db.delete(sess)
        await db.flush()


# ---- Magic links ----
async def create_magic_link(db: AsyncSession, user: User) -> MagicLink:
    link = MagicLink(
        token=random_token(32),
        user_id=user.id,
        expires_at=_now() + timedelta(seconds=settings.magic_link_ttl),
    )
    db.add(link)
    await db.flush()
    return link


async def consume_magic_link(db: AsyncSession, token: str) -> User | None:
    link = await db.get(MagicLink, token)
    if not link or link.used_at is not None or as_aware(link.expires_at) <= now():
        return None
    user = await db.get(User, link.user_id)
    if not user or not user.is_active:
        return None
    link.used_at = _now()
    await db.flush()
    return user
