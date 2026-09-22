from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OptionalSnowflake, Snowflake


class RoleActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Snowflake = Field(description="Discord ID of the member to modify")
    role_id: Snowflake = Field(description="Discord ID of the role")
    reason: str | None = Field(default=None, max_length=400)


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: OptionalSnowflake = Field(
        default=None,
        description="Member to verify; defaults to the authenticated user.",
    )


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    actor_type: str
    target_discord_id: str | None
    target_label: str | None
    message: str
    event_metadata: dict[str, Any] | None
    created_at: datetime


class LogPage(BaseModel):
    items: list[LogOut]
    total: int
    limit: int
    offset: int


class ActionResult(BaseModel):
    """Uniform response for automation endpoints."""

    ok: bool = True
    message: str
    log: LogOut | None = None
