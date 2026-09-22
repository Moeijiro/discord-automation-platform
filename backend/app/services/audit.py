"""Writes and reads the automation audit trail.

Every state change in the platform funnels through :func:`record` so the
dashboard timeline and the database never drift apart.
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActorType, AutomationLog, EventType, Guild


def record(
    db: Session,
    *,
    guild: Guild,
    event_type: EventType,
    message: str,
    actor_type: ActorType = ActorType.SYSTEM,
    target_discord_id: str | None = None,
    target_label: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> AutomationLog:
    entry = AutomationLog(
        guild_id=guild.id,
        event_type=str(event_type),
        actor_type=str(actor_type),
        message=message[:255],
        target_discord_id=target_discord_id,
        target_label=target_label,
        event_metadata=metadata,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


def recent(
    db: Session,
    *,
    guild: Guild,
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
) -> Sequence[AutomationLog]:
    stmt = (
        select(AutomationLog)
        .where(AutomationLog.guild_id == guild.id)
        .order_by(AutomationLog.created_at.desc(), AutomationLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    if event_type:
        stmt = stmt.where(AutomationLog.event_type == event_type)
    return db.execute(stmt).scalars().all()


def count_by_type(db: Session, *, guild: Guild) -> dict[str, int]:
    """Totals used by the dashboard stat tiles."""
    from sqlalchemy import func

    rows = db.execute(
        select(AutomationLog.event_type, func.count())
        .where(AutomationLog.guild_id == guild.id)
        .group_by(AutomationLog.event_type)
    ).all()
    return {event_type: total for event_type, total in rows}
