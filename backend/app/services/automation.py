"""The automations themselves.

Each one performs the same three steps in the same order:

1. check that Discord will actually allow the action (bot present, bot
   permissions, role hierarchy) -- a refusal here never reaches Discord;
2. perform it through the gateway;
3. write exactly one audit entry describing what happened.

Failures are logged too: a silent automation is worse than a loud one.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.permissions import Permission, has
from app.models import ActorType, AutomationLog, EventType, Guild, GuildSettings
from app.services import audit
from app.services.discord_gateway import DiscordError, DiscordGateway, Role

logger = logging.getLogger(__name__)

WELCOME_PLACEHOLDERS = ("{user}", "{username}", "{server}", "{member_count}")


class AutomationError(Exception):
    """A precondition failed; the caller turns this into an HTTP response."""

    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# --------------------------------------------------------------------------
# Preconditions
# --------------------------------------------------------------------------
async def ensure_bot_ready(
    guild: Guild, gateway: DiscordGateway, *required: Permission
) -> None:
    """Refuse early when the bot cannot possibly complete the action."""
    if not guild.bot_present:
        raise AutomationError(
            "The automation bot is not in this server yet. Invite it first.", 409
        )
    bits = await gateway.bot_permissions(guild.discord_id)
    missing = [flag.name for flag in required if not has(bits, flag)]
    if missing:
        raise AutomationError(
            "The bot is missing Discord permissions: " + ", ".join(missing), 409
        )


def resolve_role(roles: list[Role], role_id: str) -> Role:
    role = next((item for item in roles if item.id == role_id), None)
    if role is None:
        raise AutomationError("That role does not exist in this server.", 404)
    if role.managed:
        raise AutomationError(
            "Discord does not allow bots to assign integration-managed roles.", 409
        )
    if role.name == "@everyone":
        raise AutomationError("@everyone cannot be assigned.", 400)
    return role


async def ensure_role_assignable(
    guild: Guild, gateway: DiscordGateway, role_id: str
) -> Role:
    """A bot can only touch roles below its own highest role."""
    roles = await gateway.fetch_roles(guild.discord_id)
    role = resolve_role(roles, role_id)

    bot_member = await gateway.fetch_member(
        guild.discord_id, await gateway.bot_user_id()
    )
    if bot_member is not None:
        by_id = {item.id: item for item in roles}
        highest = max(
            (by_id[rid].position for rid in bot_member.roles if rid in by_id),
            default=0,
        )
        if role.position >= highest:
            raise AutomationError(
                f"'{role.name}' sits above the bot's highest role. "
                "Move the bot's role higher in Discord's role list.",
                409,
            )
    return role


# --------------------------------------------------------------------------
# Role automation
# --------------------------------------------------------------------------
async def apply_role_change(
    db: Session,
    *,
    guild: Guild,
    gateway: DiscordGateway,
    target_id: str,
    role_id: str,
    add: bool,
    actor_label: str,
    actor_type: ActorType = ActorType.USER,
    reason: str | None = None,
) -> AutomationLog:
    await ensure_bot_ready(guild, gateway, Permission.MANAGE_ROLES)
    role = await ensure_role_assignable(guild, gateway, role_id)

    audit_reason = reason or f"Discord Automation Platform: requested by {actor_label}"
    action = "add" if add else "remove"

    try:
        if add:
            await gateway.add_role(guild.discord_id, target_id, role_id, audit_reason)
        else:
            await gateway.remove_role(guild.discord_id, target_id, role_id, audit_reason)
    except DiscordError as exc:
        audit.record(
            db,
            guild=guild,
            event_type=EventType.AUTOMATION_FAILED,
            actor_type=actor_type,
            target_discord_id=target_id,
            message=f"Failed to {action} role '{role.name}': {exc.message}",
            metadata={"role_id": role_id, "action": action, "error": exc.message},
        )
        raise AutomationError(exc.message, exc.status_code) from exc

    return audit.record(
        db,
        guild=guild,
        event_type=EventType.ROLE_ADDED if add else EventType.ROLE_REMOVED,
        actor_type=actor_type,
        target_discord_id=target_id,
        target_label=role.name,
        message=(
            f"Role '{role.name}' {'assigned to' if add else 'removed from'} "
            f"{target_id} by {actor_label}"
        ),
        metadata={"role_id": role_id, "role_name": role.name, "actor": actor_label},
    )


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
async def run_verification(
    db: Session,
    *,
    guild: Guild,
    settings: GuildSettings,
    gateway: DiscordGateway,
    member_id: str,
    actor_label: str,
) -> AutomationLog:
    """Grant the configured verified role to a member.

    The workflow is deliberately one step -- the interesting part of a
    verification system is the guard rails around it, not the challenge.
    """
    if not settings.verification_enabled:
        raise AutomationError("Verification is disabled for this server.", 409)
    if not settings.verified_role_id:
        raise AutomationError("No verified role has been configured yet.", 409)

    member = await gateway.fetch_member(guild.discord_id, member_id)
    if member is None:
        raise AutomationError("That member is not in this server.", 404)
    if settings.verified_role_id in member.roles:
        raise AutomationError("That member is already verified.", 409)

    await apply_role_change(
        db,
        guild=guild,
        gateway=gateway,
        target_id=member_id,
        role_id=settings.verified_role_id,
        add=True,
        actor_label=actor_label,
        reason="Discord Automation Platform: verification completed",
    )

    return audit.record(
        db,
        guild=guild,
        event_type=EventType.VERIFICATION_COMPLETED,
        actor_type=ActorType.USER,
        target_discord_id=member_id,
        target_label=member.username,
        message=f"{member.username} completed verification",
        metadata={"role_id": settings.verified_role_id, "actor": actor_label},
    )


# --------------------------------------------------------------------------
# Welcome
# --------------------------------------------------------------------------
def render_welcome(
    template: str, *, member_id: str, username: str, guild_name: str, member_count: int
) -> str:
    """Substitute the supported placeholders; unknown braces are left alone."""
    return (
        template.replace("{user}", f"<@{member_id}>")
        .replace("{username}", username)
        .replace("{server}", guild_name)
        .replace("{member_count}", str(member_count))
    )[:2000]


async def handle_member_join(
    db: Session,
    *,
    guild: Guild,
    settings: GuildSettings,
    gateway: DiscordGateway,
    member_id: str,
    username: str,
    member_count: int,
) -> list[AutomationLog]:
    """Everything that should happen when someone joins the server."""
    entries = [
        audit.record(
            db,
            guild=guild,
            event_type=EventType.MEMBER_JOINED,
            actor_type=ActorType.BOT,
            target_discord_id=member_id,
            target_label=username,
            message=f"{username} joined the server",
            metadata={"member_count": member_count},
        )
    ]

    if settings.welcome_enabled and settings.welcome_channel_id:
        content = render_welcome(
            settings.welcome_message,
            member_id=member_id,
            username=username,
            guild_name=guild.name,
            member_count=member_count,
        )
        try:
            await gateway.send_message(settings.welcome_channel_id, content)
            entries.append(
                audit.record(
                    db,
                    guild=guild,
                    event_type=EventType.WELCOME_SENT,
                    actor_type=ActorType.BOT,
                    target_discord_id=member_id,
                    target_label=username,
                    message=f"Welcome message sent for {username}",
                    metadata={"channel_id": settings.welcome_channel_id},
                )
            )
        except DiscordError as exc:
            logger.warning("Welcome message failed for %s: %s", guild.discord_id, exc)
            entries.append(
                audit.record(
                    db,
                    guild=guild,
                    event_type=EventType.AUTOMATION_FAILED,
                    actor_type=ActorType.BOT,
                    target_discord_id=member_id,
                    message=f"Welcome message failed: {exc.message}",
                    metadata={"channel_id": settings.welcome_channel_id},
                )
            )

    if settings.autorole_enabled and settings.autorole_role_id:
        try:
            entries.append(
                await apply_role_change(
                    db,
                    guild=guild,
                    gateway=gateway,
                    target_id=member_id,
                    role_id=settings.autorole_role_id,
                    add=True,
                    actor_label="autorole",
                    actor_type=ActorType.BOT,
                    reason="Discord Automation Platform: join autorole",
                )
            )
        except AutomationError as exc:
            logger.warning("Autorole failed for %s: %s", guild.discord_id, exc.message)

    return entries
