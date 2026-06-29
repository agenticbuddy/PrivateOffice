"""Shared FastAPI dependencies: current-user resolution from the session cookie."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.services import auth as auth_service

settings = get_settings()


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    sid = request.cookies.get(settings.session_cookie)
    user = await auth_service.get_session_user(db, sid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user
