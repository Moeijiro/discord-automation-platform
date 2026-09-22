"""Automation endpoints: verification and manual role changes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import GuildContext, gateway_dependency, get_guild_context, require_manager
from app.core.rate_limit import RateLimiter
from app.db.session import get_db
from app.schemas.automation import ActionResult, LogOut, RoleActionRequest, VerifyRequest
from app.services import automation
from app.services.discord_gateway import DiscordGateway

router = APIRouter(prefix="/api/guilds", tags=["automation"])

verify_limit = RateLimiter(times=5, seconds=60, scope="verify")
role_limit = RateLimiter(times=20, seconds=60, scope="roles")


@router.post(
    "/{guild_id}/verify",
    response_model=ActionResult,
    summary="Run the verification workflow",
    responses={409: {"description": "Verification disabled or already verified"}},
)
async def verify(
    payload: VerifyRequest | None = None,
    context: GuildContext = Depends(get_guild_context),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(verify_limit),
) -> ActionResult:
    """Members verify themselves; verifying *someone else* needs Manage Server."""
    member_id = (payload.member_id if payload else None) or context.user.discord_id
    if member_id != context.user.discord_id and not context.can_manage:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only verify yourself in this server.",
        )

    try:
        log = await automation.run_verification(
            db,
            guild=context.guild,
            settings=context.settings,
            gateway=gateway,
            member_id=member_id,
            actor_label=context.actor_label,
        )
    except automation.AutomationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    return ActionResult(
        message="Verification complete.", log=LogOut.model_validate(log)
    )


@router.post(
    "/{guild_id}/roles/add",
    response_model=ActionResult,
    summary="Assign a role to a member",
)
async def add_role(
    payload: RoleActionRequest,
    context: GuildContext = Depends(require_manager),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(role_limit),
) -> ActionResult:
    return await _role_action(payload, context, db, gateway, add=True)


@router.post(
    "/{guild_id}/roles/remove",
    response_model=ActionResult,
    summary="Remove a role from a member",
)
async def remove_role(
    payload: RoleActionRequest,
    context: GuildContext = Depends(require_manager),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(role_limit),
) -> ActionResult:
    return await _role_action(payload, context, db, gateway, add=False)


async def _role_action(
    payload: RoleActionRequest,
    context: GuildContext,
    db: Session,
    gateway: DiscordGateway,
    *,
    add: bool,
) -> ActionResult:
    try:
        log = await automation.apply_role_change(
            db,
            guild=context.guild,
            gateway=gateway,
            target_id=payload.user_id,
            role_id=payload.role_id,
            add=add,
            actor_label=context.actor_label,
            reason=payload.reason,
        )
    except automation.AutomationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    verb = "assigned" if add else "removed"
    return ActionResult(
        message=f"Role {verb}.", log=LogOut.model_validate(log)
    )
