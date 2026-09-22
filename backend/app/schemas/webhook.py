from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Snowflake


class CustomWebhookIn(BaseModel):
    """Payload for POST /api/webhooks/custom.

    Kept deliberately small: it demonstrates signature verification, strict
    validation and audit logging rather than an event schema of its own.
    """

    model_config = ConfigDict(extra="forbid")

    event: Literal["deployment", "alert", "release", "custom"] = "custom"
    guild_id: Snowflake
    message: str = Field(min_length=1, max_length=500)
    announce_in_channel: str | None = Field(
        default=None, description="Optional channel ID to post the message to."
    )
    metadata: dict[str, Any] | None = None


class WebhookAccepted(BaseModel):
    ok: bool = True
    log_id: int
    announced: bool = False
