"""User-facing node tree: folders, sharing, permissions.

File creation/upload/download/versions are added in later blocks; this block covers
folders, the permission model and sharing.
"""
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import formats
from app.db import get_db
from app.deps import get_current_user
from app.models import Node, User
from app.schemas import (
    FileCreateIn,
    FolderCreateIn,
    NodeOut,
    NodePatchIn,
    ShareIn,
    ShareOut,
    UserDirectoryOut,
    VersionOut,
)
from app.services import audit as audit_service
from app.services import files as files_svc
from app.services import nodes as svc
from app.storage import get_storage
from app.util import content_disposition

router = APIRouter(prefix="/api", tags=["nodes"])


@router.get("/formats")
async def supported_formats(user: User = Depends(get_current_user)) -> dict:
    return {
        "creatable": [
            {"format": f, "mime": formats.EXT_MIME[f], "category": formats.category_for("x." + f)}
            for f in formats.CREATABLE
        ],
        "supported_ext": sorted(formats.EXT_MIME.keys()),
    }

ROLE_RANK = svc.ROLE_RANK


def _node_out(node: Node, role: str | None) -> NodeOut:
    out = NodeOut.model_validate(node)
    out.my_role = role
    return out


async def _require(
    db: AsyncSession, user: User, node_id: uuid.UUID, min_role: str
) -> tuple[Node, str]:
    node = await svc.get_node(db, node_id)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Node not found")
    role = await svc.effective_role(db, user.id, node)
    if role is None or ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return node, role


# ---- User directory (available to everyone, for sharing) ----
@router.get("/users", response_model=list[UserDirectoryOut])
async def user_directory(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[UserDirectoryOut]:
    res = await db.execute(
        select(User).where(User.is_active == True).order_by(User.full_name)  # noqa: E712
    )
    return [UserDirectoryOut.model_validate(u) for u in res.scalars().all()]


# ---- Listing ----
@router.get("/nodes", response_model=list[NodeOut])
async def list_nodes(
    parent: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NodeOut]:
    if parent is None:
        items = await svc.list_root(db, user.id)
        return [_node_out(n, await svc.effective_role(db, user.id, n)) for n in items]
    node, _ = await _require(db, user, parent, "reader")
    items = await svc.list_children(db, node.id)
    return [_node_out(n, await svc.effective_role(db, user.id, n)) for n in items]


@router.get("/nodes/shared-with-me", response_model=list[NodeOut])
async def shared_with_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[NodeOut]:
    items = await svc.list_shared_with_me(db, user.id)
    return [_node_out(n, await svc.effective_role(db, user.id, n)) for n in items]


@router.get("/nodes/recent", response_model=list[NodeOut])
async def recent(
    limit: int = Query(default=12, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NodeOut]:
    items = await svc.recent_files(db, user.id, limit)
    return [_node_out(n, await svc.effective_role(db, user.id, n)) for n in items]


@router.get("/nodes/search", response_model=list[NodeOut])
async def search(
    q: str = Query(min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NodeOut]:
    items = await svc.search_files(db, user.id, q)
    return [_node_out(n, await svc.effective_role(db, user.id, n)) for n in items]


# ---- Folders ----
@router.post("/nodes/folder", response_model=NodeOut, status_code=201)
async def create_folder(
    body: FolderCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeOut:
    if body.parent_id is not None:
        await _require(db, user, body.parent_id, "editor")
    node = await svc.create_folder(db, user.id, body.name, body.parent_id)
    await audit_service.record(db, actor_id=user.id, action="create_folder", node_id=node.id,
                               meta={"name": body.name})
    await db.commit()
    return _node_out(node, "owner")


# ---- Files: create / upload / download / versions ----
@router.post("/nodes/file", response_model=NodeOut, status_code=201)
async def create_file(
    body: FileCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeOut:
    if body.parent_id is not None:
        await _require(db, user, body.parent_id, "editor")
    node = await files_svc.create_blank(
        db, get_storage(), user, body.name, body.parent_id, body.format
    )
    await audit_service.record(db, actor_id=user.id, action="create_file", node_id=node.id,
                               meta={"format": body.format, "locale": user.locale})
    await db.commit()
    return _node_out(node, "owner")


@router.post("/nodes/upload", response_model=NodeOut, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    parent_id: uuid.UUID | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeOut:
    if parent_id is not None:
        await _require(db, user, parent_id, "editor")
    name = file.filename or "upload"
    if not formats.is_supported(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported format. Allowed: {', '.join(sorted(formats.EXT_MIME))}",
        )
    data = await file.read()
    node = await files_svc.upload(db, get_storage(), user, name, parent_id, data)
    await audit_service.record(db, actor_id=user.id, action="upload", node_id=node.id,
                               meta={"name": name, "size": len(data)})
    await db.commit()
    return _node_out(node, "owner")


@router.get("/nodes/{node_id}/download")
async def download_node(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    node, _ = await _require(db, user, node_id, "reader")
    if node.type != "file" or not node.storage_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a file")
    data = await files_svc.read_current(get_storage(), node)
    return Response(
        content=data,
        media_type=node.mime or "application/octet-stream",
        headers={"Content-Disposition": content_disposition(node.name)},
    )


@router.get("/nodes/{node_id}/versions", response_model=list[VersionOut])
async def node_versions(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VersionOut]:
    await _require(db, user, node_id, "reader")
    items = await files_svc.list_versions(db, node_id)
    return [VersionOut.model_validate(v) for v in items]


# ---- Detail / rename / move / delete ----
@router.get("/nodes/{node_id}", response_model=NodeOut)
async def node_detail(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeOut:
    node, role = await _require(db, user, node_id, "reader")
    return _node_out(node, role)


@router.patch("/nodes/{node_id}", response_model=NodeOut)
async def patch_node(
    node_id: uuid.UUID,
    body: NodePatchIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeOut:
    node, role = await _require(db, user, node_id, "editor")
    if body.name is not None:
        node.name = body.name
    if body.parent_id is not None and body.parent_id != node.parent_id:
        # moving requires edit rights on the destination folder
        await _require(db, user, body.parent_id, "editor")
        node.parent_id = body.parent_id
    await audit_service.record(db, actor_id=user.id, action="rename_move", node_id=node.id)
    await db.commit()
    return _node_out(node, role)


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node, _ = await _require(db, user, node_id, "owner")
    await svc.delete_node_recursive(db, node, storage=get_storage())
    await audit_service.record(db, actor_id=user.id, action="delete", node_id=None,
                               meta={"node_id": str(node_id)})
    await db.commit()


# ---- Sharing ----
@router.get("/nodes/{node_id}/shares", response_model=list[ShareOut])
async def list_shares(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ShareOut]:
    await _require(db, user, node_id, "reader")
    rows = await svc.list_shares(db, node_id)
    return [
        ShareOut(user_id=s.user_id, role=s.role, full_name=u.full_name, email=u.email)
        for (s, u) in rows
    ]


@router.put("/nodes/{node_id}/shares", response_model=ShareOut)
async def upsert_share(
    node_id: uuid.UUID,
    body: ShareIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareOut:
    await _require(db, user, node_id, "owner")
    target = await db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await svc.set_share(db, node_id, body.user_id, body.role)
    await audit_service.record(db, actor_id=user.id, action="share", node_id=node_id,
                               meta={"user_id": str(body.user_id), "role": body.role})
    await db.commit()
    return ShareOut(user_id=target.id, role=body.role, full_name=target.full_name,
                    email=target.email)


@router.delete("/nodes/{node_id}/shares/{target_id}", status_code=204)
async def delete_share(
    node_id: uuid.UUID,
    target_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require(db, user, node_id, "owner")
    await svc.remove_share(db, node_id, target_id)
    await audit_service.record(db, actor_id=user.id, action="unshare", node_id=node_id,
                               meta={"user_id": str(target_id)})
    await db.commit()
