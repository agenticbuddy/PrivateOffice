"""Audit logging helper — one place to append who/what/when entries."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    node_id: uuid.UUID | None = None,
    meta: dict | None = None,
) -> None:
    db.add(AuditLog(actor_id=actor_id, node_id=node_id, action=action, meta=meta))
    await db.flush()
