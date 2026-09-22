from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.guild_settings import GuildSettingsOut


class RoleOut(BaseModel):
    id: str
    name: str
    color: int = 0
    position: int = 0
    managed: bool = False


class ChannelOut(BaseModel):
    id: str
    name: str


class GuildSummary(BaseModel):
    """One card in the server list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    icon_url: str | None = None
    bot_present: bool = False
    manageable: bool = False
    is_owner: bool = False
    permissions: list[str] = []


class GuildDetail(GuildSummary):
    """Everything the server dashboard needs in a single request."""

    member_count: int | None = None
    presence_count: int | None = None
    roles: list[RoleOut] = []
    channels: list[ChannelOut] = []
    settings: GuildSettingsOut
    stats: dict[str, int] = {}
