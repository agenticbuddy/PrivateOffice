"""WOPI host endpoints — consumed by the editor (WOPI client) only.

CO calls these with the signed `access_token` (query param, or Bearer header). The
token carries (user, node, can_write); we re-derive permissions on every call.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import Node, User
from app.security import verify_wopi_token
from app.services import audit as audit_service
from app.services import files as files_svc
from app.services import notifications as notify_service
from app.storage import get_storage
from app.util import as_aware

settings = get_settings()
router = APIRouter(prefix="/wopi/files", tags=["wopi"])


def _token_from(request: Request, access_token: str | None) -> str | None:
    if access_token:
        return access_token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


async def _resolve(
    request: Request, node_id: uuid.UUID, access_token: str | None, db: AsyncSession
) -> tuple[Node, User, dict]:
    token = _token_from(request, access_token)
    payload = verify_wopi_token(token) if token else None
    if not payload or payload.get("n") != str(node_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid WOPI token")
    node = await db.get(Node, node_id)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    user = await db.get(User, uuid.UUID(payload["u"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return node, user, payload


@router.get("/{node_id}")
async def check_file_info(
    node_id: uuid.UUID,
    request: Request,
    access_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    node, user, payload = await _resolve(request, node_id, access_token, db)
    return JSONResponse(
        {
            "BaseFileName": node.name,
            "Size": node.size or 0,
            "OwnerId": str(node.created_by),
            "UserId": str(user.id),
            "UserFriendlyName": user.full_name,
            "UserCanWrite": bool(payload.get("w")),
            "UserCanNotWriteRelative": True,
            "PostMessageOrigin": settings.public_origin,
            "LastModifiedTime": as_aware(node.updated_at).isoformat(),
            "Version": str(node.current_version_id or ""),
        }
    )


@router.get("/{node_id}/contents")
async def get_file(
    node_id: uuid.UUID,
    request: Request,
    access_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    node, _, _ = await _resolve(request, node_id, access_token, db)
    data = await files_svc.read_current(get_storage(), node)
    return Response(content=data, media_type="application/octet-stream")


@router.post("/{node_id}/contents")
async def put_file(
    node_id: uuid.UUID,
    request: Request,
    access_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    node, user, payload = await _resolve(request, node_id, access_token, db)
    if not payload.get("w"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Read-only session")
    data = await request.body()
    version = await files_svc.new_version(db, get_storage(), node, data, user.id)
    await audit_service.record(
        db, actor_id=user.id, action="edit_save", node_id=node.id,
        meta={"size": len(data), "version": str(version.id)},
    )
    # notify the owner that a collaborator saved changes (collapsed while unread —
    # Collabora autosaves often, so one unread "edited" entry per actor with a count)
    await notify_service.notify(
        db, recipient_id=node.created_by, actor_id=user.id, node_id=node.id,
        type="edit", node_name=node.name, actor_name=user.full_name,
    )
    await db.commit()
    return JSONResponse({"LastModifiedTime": as_aware(node.updated_at).isoformat()})
