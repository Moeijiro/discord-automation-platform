"""Shared FastAPI dependencies: the authentication and permission gate.

The chain is deliberately explicit:

    cookie -> session -> user -> membership -> manage permission -> guild

Routes declare how far down that chain they need, and nothing below it can be
reached by accident.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import can_manage_guild, describe
from app.core.security import SESSION_COOKIE_NAME, read_session_token
from app.db.session import get_db
from app.models import Guild, GuildMembership, GuildSettings, User
from app.services import guilds as guild_service
from app.services.discord_gateway import DiscordGateway
from app.services.gateway_factory import get_gateway

UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Cookie"},
)


def gateway_dependency() -> DiscordGateway:
    return get_gateway()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the signed session cookie into a User, or 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise UNAUTHENTICATED

    payload = read_session_token(token)
    if not payload:
        raise UNAUTHENTICATED

    user = db.get(User, int(payload["sub"]))
    if user is None or user.discord_id != payload.get("did"):
        raise UNAUTHENTICATED
    return user


@dataclass(slots=True)
class GuildContext:
    """A guild the current user is allowed to act on."""

    user: User
    guild: Guild
    membership: GuildMembership
    settings: GuildSettings

    @property
    def can_manage(self) -> bool:
        return can_manage_guild(
            self.membership.permissions, is_owner=self.membership.is_owner
        )

    @property
    def permission_names(self) -> list[str]:
        return describe(self.membership.permissions)

    @property
    def actor_label(self) -> str:
        return f"{self.user.display_name} ({self.user.discord_id})"


def get_guild_context(
    guild_id: str = Path(description="Discord guild ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GuildContext:
    """Read access: the user must be a member of the guild we know about.

    A guild the user cannot see returns 404 rather than 403 -- a 403 would
    confirm the server exists to someone who has no business knowing.
    """
    guild = guild_service.get_guild_by_discord_id(db, guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Server not found.")

    membership = db.execute(
        select(GuildMembership).where(
            GuildMembership.user_id == user.id,
            GuildMembership.guild_id == guild.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Server not found.")

    return GuildContext(
        user=user,
        guild=guild,
        membership=membership,
        settings=guild_service.get_settings(db, guild),
    )


def require_manager(
    context: GuildContext = Depends(get_guild_context),
) -> GuildContext:
    """Write access: MANAGE_GUILD (or ownership) on the target guild."""
    if not context.can_manage:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You need the Manage Server permission in this Discord server.",
        )
    return context
