"""Per-guild automation configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guild import Guild

DEFAULT_WELCOME_MESSAGE = "Welcome to {server}, {user}! You are member #{member_count}."


class GuildSettings(Base, TimestampMixin):
    __tablename__ = "guild_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"), unique=True
    )

    # --- Verification ----------------------------------------------------
    verification_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_role_id: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    # --- Welcome ---------------------------------------------------------
    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_channel_id: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    welcome_message: Mapped[str] = mapped_column(
        Text, default=DEFAULT_WELCOME_MESSAGE
    )

    # --- Role automation --------------------------------------------------
    autorole_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    autorole_role_id: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    guild: Mapped["Guild"] = relationship(back_populates="settings")
