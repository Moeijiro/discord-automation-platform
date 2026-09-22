"""Dashboard user -- one row per Discord account that has logged in.

Discord snowflakes are stored as strings: they exceed 2^53 and would lose
precision once they reach JavaScript.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guild import GuildMembership


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64))
    global_name: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    avatar: Mapped[Optional[str]] = mapped_column(String(128), default=None)

    # OAuth material is encrypted at rest (app.core.security) and is never
    # serialised into an API response.
    access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, default=None
    )
    refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, default=None
    )
    token_expires_at: Mapped[Optional[str]] = mapped_column(String(64), default=None)

    memberships: Mapped[list["GuildMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        return self.global_name or self.username

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.username} ({self.discord_id})>"
