from __future__ import annotations

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.config import DISCORD_CDN_BASE


class UserOut(BaseModel):
    """The authenticated user. OAuth tokens are never part of this model."""

    model_config = ConfigDict(from_attributes=True)

    discord_id: str
    username: str
    global_name: str | None = None
    avatar: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_name(self) -> str:
        return self.global_name or self.username

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avatar_url(self) -> str:
        if self.avatar:
            return f"{DISCORD_CDN_BASE}/avatars/{self.discord_id}/{self.avatar}.png?size=128"
        index = (int(self.discord_id) >> 22) % 6 if self.discord_id.isdigit() else 0
        return f"{DISCORD_CDN_BASE}/embed/avatars/{index}.png"
