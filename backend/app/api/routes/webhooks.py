"""Inbound webhook endpoint.

Demonstrates how an external system (CI, monitoring, a game server) can push
an event into the platform: signed request -> strict validation -> audit
entry -> optional Discord message.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import gateway_dependency
from app.core.rate_limit import RateLimiter
from app.core.security import verify_signature
from app.db.session import get_db
from app.models import ActorType, EventType
from app.schemas.webhook import CustomWebhookIn, WebhookAccepted
from app.services import audit
from app.services import guilds as guild_service
from app.services.discord_gateway import DiscordError, DiscordGateway

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

MAX_BODY_BYTES = 16 * 1024


@router.post(
    "/custom",
    response_model=WebhookAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive a signed external event",
    responses={401: {"description": "Missing or invalid signature"}},
)
async def custom_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(RateLimiter(times=30, seconds=60, scope="webhook")),
) -> WebhookAccepted:
    """Authenticated by HMAC-SHA256 over the raw body, not by a session.

    Send ``X-Signature: sha256=<hex digest>`` computed with WEBHOOK_SECRET.
    """
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload too large.")
    # Signature is checked against the exact bytes received, before parsing.
    if not verify_signature(raw, x_signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature.")

    try:
        payload = CustomWebhookIn.model_validate(json.loads(raw or b"{}"))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(422, f"Invalid payload: {exc}") from exc

    guild = guild_service.get_guild_by_discord_id(db, payload.guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown guild.")

    announced = False
    if payload.announce_in_channel and guild.bot_present:
        try:
            await gateway.send_message(
                payload.announce_in_channel, f"**{payload.event}** — {payload.message}"
            )
            announced = True
        except DiscordError:
            announced = False

    log = audit.record(
        db,
        guild=guild,
        event_type=EventType.WEBHOOK_RECEIVED,
        actor_type=ActorType.WEBHOOK,
        target_label=payload.event,
        message=payload.message[:255],
        metadata={
            "event": payload.event,
            "announced": announced,
            **(payload.metadata or {}),
        },
    )
    return WebhookAccepted(log_id=log.id, announced=announced)
