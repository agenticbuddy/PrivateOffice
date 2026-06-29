"""Admin endpoints under /admin/api — gated by nginx BasicAuth in production.

The backend trusts requests that reach this prefix (they only arrive through the
nginx `/admin` protected location). Tests call them directly.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import AuditLog, Node, User
from app.schemas import (
    MagicLinkOut,
    NodeOut,
    PasswordIn,
    UserCreateIn,
    UserDetailOut,
    UserPatchIn,
    UserStats,
    UserSummaryOut,
)
from app.services import admin as admin_service
from app.services import audit as audit_service
from app.services import auth as auth_service
from app.services import files as files_svc
from app.services import nodes as nodes_service
from app.storage import get_storage
from app.util import as_aware, content_disposition

settings = get_settings()
router = APIRouter(prefix="/admin/api", tags=["admin"])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)) -> dict:
    return await admin_service.overview(db)


@router.get("/sessions")
async def sessions(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await admin_service.active_sessions(db)


@router.get("/activity")
async def activity(
    action: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await admin_service.activity(db, action=action, actor_id=user_id, limit=limit)


@router.get("/nodes/{node_id}/download")
async def admin_download(node_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    node = await db.get(Node, node_id)
    if not node or node.type != "file" or not node.storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    data = await files_svc.read_current(get_storage(), node)
    return Response(
        content=data,
        media_type=node.mime or "application/octet-stream",
        headers={"Content-Disposition": content_disposition(node.name)},
    )


def _summary(u: User, files: int, folders: int) -> UserSummaryOut:
    return UserSummaryOut(
        id=u.id, email=u.email, full_name=u.full_name, locale=u.locale, bio=u.bio,
        is_admin=u.is_admin, is_active=u.is_active, has_password=u.password_hash is not None,
        files=files, folders=folders,
    )


@router.get("/users", response_model=list[UserSummaryOut])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserSummaryOut]:
    rows = await admin_service.list_users(db)
    return [_summary(u, f, d) for (u, f, d) in rows]


@router.post("/users", response_model=UserSummaryOut, status_code=201)
async def create_user(body: UserCreateIn, db: AsyncSession = Depends(get_db)) -> UserSummaryOut:
    existing = await auth_service.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    user = await auth_service.create_user(
        db, email=body.email, full_name=body.full_name, locale=body.locale
    )
    await audit_service.record(db, actor_id=user.id, action="user_created", meta={"by": "admin"})
    await db.commit()
    return _summary(user, 0, 0)


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await auth_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("/users/{user_id}", response_model=UserDetailOut)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> UserDetailOut:
    user = await _get_user_or_404(db, user_id)
    stats = await admin_service.user_stats(db, user_id)
    return UserDetailOut(
        id=user.id, email=user.email, full_name=user.full_name, locale=user.locale,
        bio=user.bio, is_admin=user.is_admin, is_active=user.is_active,
        has_password=user.password_hash is not None, created_at=as_aware(user.created_at),
        stats=UserStats(**stats),
    )


@router.patch("/users/{user_id}", response_model=UserDetailOut)
async def patch_user(
    user_id: uuid.UUID, body: UserPatchIn, db: AsyncSession = Depends(get_db)
) -> UserDetailOut:
    user = await _get_user_or_404(db, user_id)
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.bio is not None:
        user.bio = body.bio
    if body.locale is not None:
        user.locale = body.locale
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    return await get_user(user_id, db)


@router.post("/users/{user_id}/magic-link", response_model=MagicLinkOut)
async def gen_magic_link(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> MagicLinkOut:
    user = await _get_user_or_404(db, user_id)
    link = await auth_service.create_magic_link(db, user)
    await audit_service.record(db, actor_id=user.id, action="magic_link_issued", meta={"by": "admin"})
    await db.commit()
    return MagicLinkOut(
        url=f"{settings.public_origin}/login?magic={link.token}",
        expires_at=as_aware(link.expires_at),
    )


@router.post("/users/{user_id}/password", response_model=UserSummaryOut)
async def set_user_password(
    user_id: uuid.UUID, body: PasswordIn, db: AsyncSession = Depends(get_db)
) -> UserSummaryOut:
    user = await _get_user_or_404(db, user_id)
    await auth_service.set_password(db, user, body.password)
    await audit_service.record(db, actor_id=user.id, action="password_set", meta={"by": "admin"})
    await db.commit()
    return _summary(user, 0, 0)


@router.get("/users/{user_id}/nodes", response_model=list[NodeOut])
async def list_user_nodes(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[NodeOut]:
    await _get_user_or_404(db, user_id)
    items = await admin_service.user_nodes(db, user_id)
    return [NodeOut.model_validate(n) for n in items]


@router.delete("/users/{user_id}/nodes/{node_id}", status_code=204)
async def delete_user_node(
    user_id: uuid.UUID, node_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    await _get_user_or_404(db, user_id)
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Node not found")
    from app.storage import get_storage

    await nodes_service.delete_node_recursive(db, node, storage=get_storage())
    await db.commit()


@router.get("/users/{user_id}/audit")
async def user_audit(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    await _get_user_or_404(db, user_id)
    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.actor_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    return [
        {
            "action": a.action,
            "node_id": str(a.node_id) if a.node_id else None,
            "meta": a.meta,
            "created_at": as_aware(a.created_at).isoformat(),
        }
        for a in res.scalars().all()
    ]
