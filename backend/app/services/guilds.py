"""Guild bookkeeping: mirror Discord's view of a user's guilds into the DB.

The database is a cache, not the source of truth. Memberships are rewritten
from Discord on every login, so a user who loses MANAGE_GUILD loses dashboard
access on their next request rather than whenever a cache happens to expire.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DISCORD_CDN_BASE
from app.models import Guild, GuildMembership, GuildSettings, User
from app.services.discord_gateway import PartialGuild


def get_or_create_guild(db: Session, partial: PartialGuild) -> Guild:
    guild = db.execute(
        select(Guild).where(Guild.discord_id == partial.id)
    ).scalar_one_or_none()
    if guild is None:
        guild = Guild(discord_id=partial.id, name=partial.name, icon=partial.icon)
        db.add(guild)
        db.flush()
    else:  # names and icons change; keep the cache honest
        guild.name = partial.name
        guild.icon = partial.icon
    return guild


def get_guild_by_discord_id(db: Session, discord_id: str) -> Guild | None:
    return db.execute(
        select(Guild).where(Guild.discord_id == discord_id)
    ).scalar_one_or_none()


def get_settings(db: Session, guild: Guild) -> GuildSettings:
    """Settings rows are created lazily on first access."""
    if guild.settings is None:
        settings_row = GuildSettings(guild_id=guild.id)
        db.add(settings_row)
        db.commit()
        db.refresh(guild)
    return guild.settings


def get_membership(db: Session, user: User, guild: Guild) -> GuildMembership | None:
    return db.execute(
        select(GuildMembership).where(
            GuildMembership.user_id == user.id,
            GuildMembership.guild_id == guild.id,
        )
    ).scalar_one_or_none()


def sync_user_guilds(
    db: Session,
    user: User,
    partials: list[PartialGuild],
    bot_guild_ids: set[str],
) -> list[Guild]:
    """Replace the user's cached memberships with what Discord just reported."""
    seen: list[Guild] = []
    keep_ids: set[int] = set()

    for partial in partials:
        guild = get_or_create_guild(db, partial)
        guild.bot_present = partial.id in bot_guild_ids

        membership = get_membership(db, user, guild)
        if membership is None:
            membership = GuildMembership(user_id=user.id, guild_id=guild.id)
            db.add(membership)
        membership.permissions = partial.permissions
        membership.is_owner = partial.owner

        keep_ids.add(guild.id)
        seen.append(guild)

    # Guilds the user left (or was removed from) must not linger.
    for stale in list(user.memberships):
        if stale.guild_id not in keep_ids:
            db.delete(stale)

    db.commit()
    return seen


def icon_url(guild: Guild) -> str | None:
    """Discord CDN URL for the guild icon, or None so the UI can fall back."""
    if not guild.icon:
        return None
    return f"{DISCORD_CDN_BASE}/icons/{guild.discord_id}/{guild.icon}.png?size=128"
