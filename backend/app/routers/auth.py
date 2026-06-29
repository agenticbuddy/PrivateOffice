"""Auth endpoints: password login, magic-link login, password set, locale, me."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, MePatchIn, PasswordIn, UserOut
from app.services import audit as audit_service
from app.services import auth as auth_service

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        locale=user.locale,
        design=getattr(user, "design", None) or "glass",
        bio=user.bio,
        is_admin=user.is_admin,
        is_active=user.is_active,
        has_password=user.password_hash is not None,
    )


def _set_session_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        settings.session_cookie,
        sid,
        max_age=settings.session_ttl,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginIn, response: Response, db: AsyncSession = Depends(get_db)
) -> UserOut:
    user = await auth_service.authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    sid = await auth_service.create_session(db, user)
    await audit_service.record(db, actor_id=user.id, action="login", meta={"via": "password"})
    await db.commit()
    _set_session_cookie(response, sid)
    return _user_out(user)


@router.post("/magic/{token}", response_model=UserOut)
async def magic_login(
    token: str, response: Response, db: AsyncSession = Depends(get_db)
) -> UserOut:
    user = await auth_service.consume_magic_link(db, token)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired link")
    sid = await auth_service.create_session(db, user)
    await audit_service.record(db, actor_id=user.id, action="login", meta={"via": "magic_link"})
    await db.commit()
    _set_session_cookie(response, sid)
    return _user_out(user)


@router.post("/password", response_model=UserOut)
async def set_own_password(
    body: PasswordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    await auth_service.set_password(db, user, body.password)
    await audit_service.record(db, actor_id=user.id, action="password_set", meta={"by": "self"})
    await db.commit()
    return _user_out(user)


@router.post("/logout")
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    sid = request.cookies.get(settings.session_cookie)
    user = await auth_service.get_session_user(db, sid)
    await auth_service.delete_session(db, sid)
    if user:
        await audit_service.record(db, actor_id=user.id, action="logout")
    await db.commit()
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: MePatchIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if body.locale is not None:
        user.locale = body.locale
    if body.design is not None:
        user.design = body.design
    await db.commit()
    return _user_out(user)
