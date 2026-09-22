"""Guilds the platform knows about, and each user's access to them."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.automation_log import AutomationLog
    from app.models.guild_settings import GuildSettings
    from app.models.user import User


class Guild(Base, TimestampMixin):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    icon: Mapped[Optional[str]] = mapped_column(String(128), default=None)
    # Whether the bot is a member of this guild (refreshed from the Discord API).
    bot_present: Mapped[bool] = mapped_column(Boolean, default=False)

    settings: Mapped[Optional["GuildSettings"]] = relationship(
        back_populates="guild", cascade="all, delete-orphan", uselist=False
    )
    memberships: Mapped[list["GuildMembership"]] = relationship(
        back_populates="guild", cascade="all, delete-orphan"
    )
    logs: Mapped[list["AutomationLog"]] = relationship(
        back_populates="guild", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Guild {self.name} ({self.discord_id})>"


class GuildMembership(Base, TimestampMixin):
    """A user's cached access to a guild.

    ``permissions`` is the raw Discord permission bitfield as returned by
    ``GET /users/@me/guilds``; it is re-fetched on every login so a user who
    loses their admin role loses dashboard access too.
    """

    __tablename__ = "guild_memberships"
    __table_args__ = (UniqueConstraint("user_id", "guild_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))
    permissions: Mapped[str] = mapped_column(String(32), default="0")
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    guild: Mapped["Guild"] = relationship(back_populates="memberships")
