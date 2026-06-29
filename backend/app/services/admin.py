"""Admin-facing queries: user listing, per-user statistics, node management,
system overview, active sessions and the global activity feed."""
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, FileVersion, Node, Session, Share, User
from app.util import as_aware, now


async def list_users(db: AsyncSession) -> list[tuple[User, int, int]]:
    """All users with (files, folders) counts.

    Counts are computed in a single grouped query (not per-user) to avoid an N+1 that
    makes the admin list slow with many users.
    """
    res = await db.execute(select(User).order_by(User.created_at))
    users = list(res.scalars().all())

    grouped = await db.execute(
        select(Node.created_by, Node.type, func.count())
        .group_by(Node.created_by, Node.type)
    )
    counts: dict[tuple, int] = {}
    for uid, ntype, n in grouped.all():
        counts[(uid, ntype)] = int(n)

    return [
        (u, counts.get((u.id, "file"), 0), counts.get((u.id, "folder"), 0))
        for u in users
    ]


async def _count_nodes(db: AsyncSession, user_id: uuid.UUID, ntype: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(Node)
        .where(Node.created_by == user_id, Node.type == ntype)
    )
    return int(res.scalar_one())


async def user_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    files = await _count_nodes(db, user_id, "file")
    folders = await _count_nodes(db, user_id, "folder")

    shared_out = await db.execute(
        select(func.count())
        .select_from(Share)
        .join(Node, Node.id == Share.node_id)
        .where(Node.created_by == user_id, Share.user_id != user_id)
    )
    versions = await db.execute(
        select(func.count())
        .select_from(FileVersion)
        .join(Node, Node.id == FileVersion.node_id)
        .where(Node.created_by == user_id)
    )
    return {
        "files": files,
        "folders": folders,
        "shared_out": int(shared_out.scalar_one()),
        "versions": int(versions.scalar_one()),
    }


async def user_nodes(db: AsyncSession, user_id: uuid.UUID) -> list[Node]:
    res = await db.execute(
        select(Node).where(Node.created_by == user_id).order_by(Node.type, Node.name)
    )
    return list(res.scalars().all())


async def _scalar(db: AsyncSession, stmt) -> int:
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


async def overview(db: AsyncSession) -> dict:
    """System-wide statistics for the admin dashboard."""
    n = now()
    week_ago = n - timedelta(days=7)

    users = await _scalar(db, select(func.count()).select_from(User))
    active_users = await _scalar(
        db, select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    )
    admins = await _scalar(
        db, select(func.count()).select_from(User).where(User.is_admin == True)  # noqa: E712
    )
    with_password = await _scalar(
        db, select(func.count()).select_from(User).where(User.password_hash.is_not(None))
    )
    files = await _scalar(
        db, select(func.count()).select_from(Node).where(Node.type == "file")
    )
    folders = await _scalar(
        db, select(func.count()).select_from(Node).where(Node.type == "folder")
    )
    versions = await _scalar(db, select(func.count()).select_from(FileVersion))
    shares = await _scalar(db, select(func.count()).select_from(Share))
    current_bytes = await _scalar(
        db, select(func.coalesce(func.sum(Node.size), 0)).where(Node.type == "file")
    )
    online = await _scalar(
        db,
        select(func.count(func.distinct(Session.user_id))).where(Session.expires_at > n),
    )
    logins_7d = await _scalar(
        db,
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "login", AuditLog.created_at > week_ago),
    )
    return {
        "users": users,
        "active_users": active_users,
        "admins": admins,
        "with_password": with_password,
        "files": files,
        "folders": folders,
        "versions": versions,
        "shares": shares,
        "current_bytes": current_bytes,
        "online": online,
        "logins_7d": logins_7d,
    }


async def active_sessions(db: AsyncSession) -> list[dict]:
    """Users with at least one non-expired session ("who is online"), latest first."""
    n = now()
    res = await db.execute(
        select(User, func.max(Session.created_at), func.count(Session.id))
        .join(Session, Session.user_id == User.id)
        .where(Session.expires_at > n)
        .group_by(User.id)
        .order_by(func.max(Session.created_at).desc())
    )
    out = []
    for user, last, count in res.all():
        out.append(
            {
                "user_id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "since": as_aware(last).isoformat() if last else None,
                "sessions": int(count),
            }
        )
    return out


async def activity(
    db: AsyncSession,
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[dict]:
    """Global audit feed with the actor's name resolved."""
    stmt = (
        select(AuditLog, User)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    res = await db.execute(stmt)
    out = []
    for entry, user in res.all():
        out.append(
            {
                "id": entry.id,
                "action": entry.action,
                "actor_id": str(entry.actor_id) if entry.actor_id else None,
                "actor_name": user.full_name if user else None,
                "actor_email": user.email if user else None,
                "node_id": str(entry.node_id) if entry.node_id else None,
                "meta": entry.meta,
                "created_at": as_aware(entry.created_at).isoformat(),
            }
        )
    return out
