"""Notification inbox API — list the current user's notifications and mark them read."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Notification, User
from app.schemas import NotificationListOut, NotificationOut
from app.services import notifications as svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _out(n: Notification) -> NotificationOut:
    meta = n.meta or {}
    return NotificationOut(
        id=n.id,
        type=n.type,
        actor_id=n.actor_id,
        actor_name=meta.get("actor_name"),
        node_id=n.node_id,
        node_name=meta.get("node_name"),
        role=meta.get("role"),
        count=int(meta.get("count", 1)),
        read=n.read_at is not None,
        created_at=n.created_at,
    )


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    items = await svc.list_for(db, user.id)
    unread = await svc.unread_count(db, user.id)
    return NotificationListOut(items=[_out(n) for n in items], unread=unread)


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.mark_all_read(db, user.id)
    await db.commit()


@router.post("/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_one_read(
    notif_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.mark_read(db, user.id, notif_id)
    await db.commit()
