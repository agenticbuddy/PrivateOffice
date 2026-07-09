"""Notification inbox — raise, list, and mark-read per-user entries.

A notification is created whenever someone acts on a document that belongs to (or was
shared with) another user. Four event types, matching the audit actions they piggy-back
on: ``view`` (someone opened your doc), ``edit`` (someone saved changes to your doc),
``share`` (you were granted access) and ``unshare`` (your access was revoked).

``notify`` never notifies a user about their own action (recipient == actor is dropped).
High-frequency ``view``/``edit`` events are COLLAPSED: while an unread entry already
exists for the same (recipient, node, actor, type), we bump its timestamp and increment
``meta.count`` instead of inserting a new row — otherwise Collabora's autosave alone would
flood the owner's inbox. ``share``/``unshare`` are discrete and never collapsed.
"""
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.util import now

_COLLAPSIBLE = {"view", "edit"}


async def notify(
    db: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    node_id: uuid.UUID | None,
    type: str,
    node_name: str,
    actor_name: str,
    role: str | None = None,
) -> None:
    """Raise a notification for ``recipient_id`` (no-op if recipient == actor)."""
    if actor_id is not None and recipient_id == actor_id:
        return

    if type in _COLLAPSIBLE:
        existing = (
            await db.execute(
                select(Notification)
                .where(
                    Notification.user_id == recipient_id,
                    Notification.node_id == node_id,
                    Notification.actor_id == actor_id,
                    Notification.type == type,
                    Notification.read_at.is_(None),
                )
                .order_by(Notification.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            meta = dict(existing.meta or {})
            meta["count"] = int(meta.get("count", 1)) + 1
            meta["node_name"] = node_name  # keep the latest name
            meta["actor_name"] = actor_name
            existing.meta = meta
            existing.created_at = now()
            await db.flush()
            return

    meta: dict = {"node_name": node_name, "actor_name": actor_name}
    if role:
        meta["role"] = role
    db.add(
        Notification(
            user_id=recipient_id,
            actor_id=actor_id,
            node_id=node_id,
            type=type,
            meta=meta,
        )
    )
    await db.flush()


async def list_for(db: AsyncSession, user_id: uuid.UUID, limit: int = 30) -> list[Notification]:
    rows = (
        await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            )
        ).scalar_one()
    )


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=now())
    )
    await db.flush()


async def mark_read(db: AsyncSession, user_id: uuid.UUID, notif_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now())
    )
    await db.flush()
