from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import OptionalSnowflake
from app.services.automation import WELCOME_PLACEHOLDERS


class GuildSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_enabled: bool
    verified_role_id: str | None
    welcome_enabled: bool
    welcome_channel_id: str | None
    welcome_message: str
    autorole_enabled: bool
    autorole_role_id: str | None


class GuildSettingsUpdate(BaseModel):
    """PATCH body -- every field optional, but the combinations are checked.

    Enabling an automation without the id it depends on would create a
    configuration that silently never runs, so it is rejected here rather than
    discovered later in the audit log.
    """

    model_config = ConfigDict(extra="forbid")

    verification_enabled: bool | None = None
    verified_role_id: OptionalSnowflake = None
    welcome_enabled: bool | None = None
    welcome_channel_id: OptionalSnowflake = None
    welcome_message: str | None = Field(default=None, max_length=2000)
    autorole_enabled: bool | None = None
    autorole_role_id: OptionalSnowflake = None

    @model_validator(mode="after")
    def _check_dependencies(self) -> "GuildSettingsUpdate":
        if self.verification_enabled and self.verified_role_id is None:
            raise ValueError("verified_role_id is required to enable verification")
        if self.welcome_enabled and self.welcome_channel_id is None:
            raise ValueError("welcome_channel_id is required to enable welcome messages")
        if self.autorole_enabled and self.autorole_role_id is None:
            raise ValueError("autorole_role_id is required to enable autorole")
        if self.welcome_message is not None and not self.welcome_message.strip():
            raise ValueError("welcome_message cannot be blank")
        return self

    @property
    def placeholders(self) -> tuple[str, ...]:
        return WELCOME_PLACEHOLDERS
