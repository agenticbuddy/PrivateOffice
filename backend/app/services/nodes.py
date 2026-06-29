"""Node tree helpers shared by the admin and user-facing node features.

Holds permission resolution and the folder/file CRUD. Permission model: a user's
effective role on a node is the strongest of the implicit owner role (if they created
the node or any ancestor) and any explicit share grant on the node or an ancestor.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FileVersion, Node, Share

ROLE_RANK = {"reader": 1, "editor": 2, "owner": 3}


def stronger(a: str | None, b: str | None) -> str | None:
    """Return the more permissive of two roles (None = no access)."""
    ra, rb = ROLE_RANK.get(a or "", 0), ROLE_RANK.get(b or "", 0)
    return a if ra >= rb else b


async def effective_role(
    db: AsyncSession, user_id: uuid.UUID, node: Node
) -> str | None:
    """Resolve the user's strongest role on a node, walking up the ancestor chain.

    Walks parent links (bounded) collecting implicit-owner (created_by) and explicit
    share grants for the user; returns the most permissive role found, or None.
    """
    role: str | None = None
    current: Node | None = node
    seen: set[uuid.UUID] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if current.created_by == user_id:
            role = stronger(role, "owner")
        share = await db.get(Share, (current.id, user_id))
        if share is not None:
            role = stronger(role, share.role)
        if role == "owner" or current.parent_id is None:
            break
        current = await db.get(Node, current.parent_id)
    return role


async def get_node(db: AsyncSession, node_id: uuid.UUID) -> Node | None:
    return await db.get(Node, node_id)


async def list_root(db: AsyncSession, user_id: uuid.UUID) -> list[Node]:
    """Top-level nodes the user owns (their personal root)."""
    res = await db.execute(
        select(Node)
        .where(Node.parent_id.is_(None), Node.created_by == user_id)
        .order_by(Node.type, Node.name)
    )
    return list(res.scalars().all())


async def list_children(db: AsyncSession, parent_id: uuid.UUID) -> list[Node]:
    res = await db.execute(
        select(Node).where(Node.parent_id == parent_id).order_by(Node.type, Node.name)
    )
    return list(res.scalars().all())


async def _accessible_files_stmt(user_id: uuid.UUID):
    """Files the user owns or that are directly shared with them."""
    from sqlalchemy import or_

    shared = select(Share.node_id).where(Share.user_id == user_id)
    return select(Node).where(
        Node.type == "file",
        or_(Node.created_by == user_id, Node.id.in_(shared)),
    )


async def recent_files(db: AsyncSession, user_id: uuid.UUID, limit: int = 12) -> list[Node]:
    stmt = (await _accessible_files_stmt(user_id)).order_by(Node.updated_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def search_files(
    db: AsyncSession, user_id: uuid.UUID, q: str, limit: int = 30
) -> list[Node]:
    stmt = (
        (await _accessible_files_stmt(user_id))
        .where(Node.name.ilike(f"%{q}%"))
        .order_by(Node.updated_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_shared_with_me(db: AsyncSession, user_id: uuid.UUID) -> list[Node]:
    """Nodes explicitly shared with the user (entry points they don't own)."""
    res = await db.execute(
        select(Node)
        .join(Share, Share.node_id == Node.id)
        .where(Share.user_id == user_id, Node.created_by != user_id)
        .order_by(Node.type, Node.name)
    )
    return list(res.scalars().all())


async def create_folder(
    db: AsyncSession, user_id: uuid.UUID, name: str, parent_id: uuid.UUID | None
) -> Node:
    node = Node(type="folder", name=name, parent_id=parent_id, created_by=user_id)
    db.add(node)
    await db.flush()
    return node


# ---- Sharing ----
async def set_share(
    db: AsyncSession, node_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> Share:
    share = await db.get(Share, (node_id, user_id))
    if share is None:
        share = Share(node_id=node_id, user_id=user_id, role=role)
        db.add(share)
    else:
        share.role = role
    await db.flush()
    return share


async def remove_share(db: AsyncSession, node_id: uuid.UUID, user_id: uuid.UUID) -> None:
    share = await db.get(Share, (node_id, user_id))
    if share is not None:
        await db.delete(share)
        await db.flush()


async def list_shares(db: AsyncSession, node_id: uuid.UUID) -> list[tuple[Share, "User"]]:
    from app.models import User

    res = await db.execute(
        select(Share, User)
        .join(User, User.id == Share.user_id)
        .where(Share.node_id == node_id)
        .order_by(User.full_name)
    )
    return [(s, u) for s, u in res.all()]


async def get_descendant_ids(db: AsyncSession, root_id: uuid.UUID) -> list[uuid.UUID]:
    """Return root_id plus all descendant node ids (breadth-first)."""
    ids: list[uuid.UUID] = [root_id]
    frontier = [root_id]
    while frontier:
        res = await db.execute(select(Node.id).where(Node.parent_id.in_(frontier)))
        children = [row[0] for row in res.all()]
        if not children:
            break
        ids.extend(children)
        frontier = children
    return ids


async def collect_storage_keys(db: AsyncSession, node_ids: list[uuid.UUID]) -> list[str]:
    """Gather every MinIO object key (current + versions) under the given nodes."""
    keys: list[str] = []
    res = await db.execute(
        select(Node.storage_key).where(Node.id.in_(node_ids), Node.storage_key.is_not(None))
    )
    keys.extend(row[0] for row in res.all())
    res = await db.execute(
        select(FileVersion.storage_key).where(FileVersion.node_id.in_(node_ids))
    )
    keys.extend(row[0] for row in res.all())
    return keys


async def delete_node_recursive(db: AsyncSession, node: Node, storage=None) -> list[str]:
    """Delete a node, its descendants, their shares and versions.

    Done explicitly (not via DB cascade) for portability across PG/SQLite. Returns the
    storage keys that were removed; if a ``storage`` purger is supplied, also deletes
    the bytes from object storage.
    """
    node_ids = await get_descendant_ids(db, node.id)
    keys = await collect_storage_keys(db, node_ids)

    from sqlalchemy import delete

    await db.execute(delete(Share).where(Share.node_id.in_(node_ids)))
    await db.execute(delete(FileVersion).where(FileVersion.node_id.in_(node_ids)))
    # delete children before parents to respect FK ordering
    for nid in reversed(node_ids):
        obj = await db.get(Node, nid)
        if obj is not None:
            await db.delete(obj)
    await db.flush()

    if storage is not None and keys:
        storage.delete_objects(keys)
    return keys
