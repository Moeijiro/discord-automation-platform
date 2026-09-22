"""Server list, server detail, settings and logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    GuildContext,
    gateway_dependency,
    get_current_user,
    get_guild_context,
    require_manager,
)
from app.core.permissions import can_manage_guild, describe
from app.core.rate_limit import RateLimiter
from app.db.session import get_db
from app.models import ActorType, AutomationLog, EventType, User
from app.schemas.automation import LogOut, LogPage
from app.schemas.guild import ChannelOut, GuildDetail, GuildSummary, RoleOut
from app.schemas.guild_settings import GuildSettingsOut, GuildSettingsUpdate
from app.services import audit
from app.services import guilds as guild_service
from app.services.discord_gateway import DiscordError, DiscordGateway

router = APIRouter(prefix="/api/guilds", tags=["guilds"])

settings_limit = RateLimiter(times=20, seconds=60, scope="settings")


@router.get("", response_model=list[GuildSummary], summary="Servers the user can see")
def list_guilds(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[GuildSummary]:
    """Cached from the last login; POST /api/auth/refresh-guilds re-syncs it."""
    summaries = []
    for membership in user.memberships:
        guild = membership.guild
        summaries.append(
            GuildSummary(
                id=guild.discord_id,
                name=guild.name,
                icon_url=guild_service.icon_url(guild),
                bot_present=guild.bot_present,
                manageable=can_manage_guild(
                    membership.permissions, is_owner=membership.is_owner
                ),
                is_owner=membership.is_owner,
                permissions=describe(membership.permissions),
            )
        )
    # Manageable servers first, then alphabetically.
    return sorted(summaries, key=lambda item: (not item.manageable, item.name.lower()))


@router.get("/{guild_id}", response_model=GuildDetail, summary="Server dashboard data")
async def get_guild(
    context: GuildContext = Depends(get_guild_context),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
) -> GuildDetail:
    guild = context.guild
    detail = GuildDetail(
        id=guild.discord_id,
        name=guild.name,
        icon_url=guild_service.icon_url(guild),
        bot_present=guild.bot_present,
        manageable=context.can_manage,
        is_owner=context.membership.is_owner,
        permissions=context.permission_names,
        settings=GuildSettingsOut.model_validate(context.settings),
        stats=audit.count_by_type(db, guild=guild),
    )

    # Roles and channels only exist for us once the bot is in the server.
    if guild.bot_present and context.can_manage:
        try:
            info = await gateway.fetch_guild(guild.discord_id)
            detail.member_count = info.get("approximate_member_count")
            detail.presence_count = info.get("approximate_presence_count")
            detail.roles = [
                RoleOut(**role.__dict__)
                for role in await gateway.fetch_roles(guild.discord_id)
                if role.name != "@everyone"
            ]
            detail.channels = [
                ChannelOut(id=channel.id, name=channel.name)
                for channel in await gateway.fetch_channels(guild.discord_id)
            ]
        except DiscordError:
            # A degraded dashboard beats a 502: settings and logs still render.
            detail.roles = []
            detail.channels = []
    return detail


@router.get(
    "/{guild_id}/settings",
    response_model=GuildSettingsOut,
    summary="Automation settings",
)
def get_settings(context: GuildContext = Depends(get_guild_context)) -> GuildSettingsOut:
    return GuildSettingsOut.model_validate(context.settings)


@router.patch(
    "/{guild_id}/settings",
    response_model=GuildSettingsOut,
    summary="Update automation settings",
)
async def update_settings(
    payload: GuildSettingsUpdate,
    context: GuildContext = Depends(require_manager),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(settings_limit),
) -> GuildSettingsOut:
    """Apply a partial update, after checking the ids exist in the guild."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update.")

    await _validate_references(context, gateway, changes)

    applied: dict[str, object] = {}
    for field, value in changes.items():
        if getattr(context.settings, field) != value:
            setattr(context.settings, field, value)
            applied[field] = value
    db.commit()
    db.refresh(context.settings)

    if applied:
        audit.record(
            db,
            guild=context.guild,
            event_type=EventType.SETTINGS_UPDATED,
            actor_type=ActorType.USER,
            target_discord_id=context.user.discord_id,
            target_label=context.user.display_name,
            message=f"{context.user.display_name} updated {', '.join(applied)}",
            metadata={"changed": applied},
        )
    return GuildSettingsOut.model_validate(context.settings)


async def _validate_references(
    context: GuildContext, gateway: DiscordGateway, changes: dict
) -> None:
    """Reject role/channel ids that do not belong to this guild."""
    if not context.guild.bot_present:
        return
    try:
        role_ids = {role.id for role in await gateway.fetch_roles(context.guild.discord_id)}
        channel_ids = {
            channel.id for channel in await gateway.fetch_channels(context.guild.discord_id)
        }
    except DiscordError:
        return  # do not block configuration on a transient Discord outage

    for field in ("verified_role_id", "autorole_role_id"):
        value = changes.get(field)
        if value and value not in role_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{field} does not match a role in this server.",
            )
    channel = changes.get("welcome_channel_id")
    if channel and channel not in channel_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "welcome_channel_id does not match a text channel in this server.",
        )


@router.get("/{guild_id}/logs", response_model=LogPage, summary="Audit trail")
def get_logs(
    context: GuildContext = Depends(get_guild_context),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None, max_length=48),
) -> LogPage:
    items = audit.recent(
        db, guild=context.guild, limit=limit, offset=offset, event_type=event_type
    )
    total_stmt = select(func.count()).where(AutomationLog.guild_id == context.guild.id)
    if event_type:
        total_stmt = total_stmt.where(AutomationLog.event_type == event_type)
    total = db.execute(total_stmt).scalar_one()

    return LogPage(
        items=[LogOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
