"""Append-only audit trail for everything the automation does."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.guild import Guild


class EventType(StrEnum):
    """Stable identifiers written to the audit trail."""

    VERIFICATION_COMPLETED = "verification_completed"
    ROLE_ADDED = "role_added"
    ROLE_REMOVED = "role_removed"
    MEMBER_JOINED = "member_joined"
    WELCOME_SENT = "welcome_sent"
    SETTINGS_UPDATED = "settings_updated"
    WEBHOOK_RECEIVED = "webhook_received"
    AUTOMATION_FAILED = "automation_failed"


class ActorType(StrEnum):
    """Who triggered the event."""

    USER = "user"          # a dashboard action
    BOT = "bot"            # a gateway event handled by the bot
    WEBHOOK = "webhook"    # an external integration
    SYSTEM = "system"


class AutomationLog(Base):
    __tablename__ = "automation_logs"
    __table_args__ = (
        Index("ix_logs_guild_created", "guild_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))

    event_type: Mapped[str] = mapped_column(String(48), index=True)
    actor_type: Mapped[str] = mapped_column(String(16), default=ActorType.SYSTEM)

    # Subject of the event: the Discord user it happened to.
    target_discord_id: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    target_label: Mapped[Optional[str]] = mapped_column(String(128), default=None)

    message: Mapped[str] = mapped_column(String(255), default="")
    event_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    guild: Mapped["Guild"] = relationship(back_populates="logs")
