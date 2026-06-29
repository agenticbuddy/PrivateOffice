"""File lifecycle: create blank, upload, version snapshots, read bytes.

Each saved state (initial + every editor PutFile) becomes a ``FileVersion`` with its
own object in MinIO; ``nodes.storage_key`` always points at the latest ("current")
object. Storage is sync boto3, wrapped in a threadpool to stay non-blocking.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app import formats
from app.models import FileVersion, Node, User
from app.services import templates
from app.storage import Storage


def _current_key(node_id: uuid.UUID) -> str:
    return f"nodes/{node_id}/current"


def _version_key(node_id: uuid.UUID, version_id: uuid.UUID) -> str:
    return f"nodes/{node_id}/versions/{version_id}"


async def new_version(
    db: AsyncSession,
    storage: Storage,
    node: Node,
    data: bytes,
    author_id: uuid.UUID | None,
) -> FileVersion:
    """Persist a new saved state: a version snapshot + overwrite current."""
    version = FileVersion(node_id=node.id, storage_key="", size=len(data), author_id=author_id)
    db.add(version)
    await db.flush()

    vkey = _version_key(node.id, version.id)
    await run_in_threadpool(storage.put_bytes, vkey, data, node.mime)
    version.storage_key = vkey

    await run_in_threadpool(storage.put_bytes, _current_key(node.id), data, node.mime)
    node.storage_key = _current_key(node.id)
    node.size = len(data)
    node.current_version_id = version.id
    await db.flush()
    return version


async def create_blank(
    db: AsyncSession,
    storage: Storage,
    user: User,
    name: str,
    parent_id: uuid.UUID | None,
    fmt: str,
) -> Node:
    locale = user.locale or "en"
    data = templates.blank_document(fmt)
    if not name.lower().endswith("." + fmt):
        name = f"{name}.{fmt}"
    node = Node(
        type="file", name=name, parent_id=parent_id, created_by=user.id,
        co_format=fmt, mime=formats.EXT_MIME[fmt], creator_locale=locale,
    )
    db.add(node)
    await db.flush()
    await new_version(db, storage, node, data, user.id)
    return node


async def upload(
    db: AsyncSession,
    storage: Storage,
    user: User,
    name: str,
    parent_id: uuid.UUID | None,
    data: bytes,
) -> Node:
    ext = formats.ext_of(name)
    node = Node(
        type="file", name=name, parent_id=parent_id, created_by=user.id,
        co_format=ext, mime=formats.EXT_MIME[ext], creator_locale=user.locale or "en",
    )
    db.add(node)
    await db.flush()
    await new_version(db, storage, node, data, user.id)
    return node


async def read_current(storage: Storage, node: Node) -> bytes:
    return await run_in_threadpool(storage.get_bytes, node.storage_key)


async def list_versions(db: AsyncSession, node_id: uuid.UUID) -> list[FileVersion]:
    res = await db.execute(
        select(FileVersion)
        .where(FileVersion.node_id == node_id)
        .order_by(FileVersion.created_at.desc())
    )
    return list(res.scalars().all())
