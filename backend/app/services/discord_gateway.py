"""The contract every Discord implementation honours.

Both the live REST client and the demo client implement ``DiscordGateway``, so
routes, automations and the bot never branch on which mode is active.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class DiscordError(Exception):
    """A call to Discord failed in a way the caller should surface."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(slots=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 604800
    scope: str = ""


@dataclass(slots=True)
class DiscordUser:
    id: str
    username: str
    global_name: str | None = None
    avatar: str | None = None


@dataclass(slots=True)
class PartialGuild:
    id: str
    name: str
    icon: str | None = None
    owner: bool = False
    permissions: str = "0"


@dataclass(slots=True)
class Role:
    id: str
    name: str
    color: int = 0
    position: int = 0
    managed: bool = False


@dataclass(slots=True)
class Channel:
    id: str
    name: str
    type: int = 0


@dataclass(slots=True)
class GuildMember:
    id: str
    username: str
    roles: list[str] = field(default_factory=list)
    joined_at: str | None = None


@runtime_checkable
class DiscordGateway(Protocol):
    """Everything the platform needs from Discord."""

    is_mock: bool

    # --- OAuth ------------------------------------------------------------
    def authorize_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> OAuthTokens: ...
    async def fetch_current_user(self, access_token: str) -> DiscordUser: ...
    async def fetch_user_guilds(self, access_token: str) -> list[PartialGuild]: ...

    # --- Bot (application token) -----------------------------------------
    async def bot_guild_ids(self) -> set[str]: ...
    async def fetch_guild(self, guild_id: str) -> dict[str, Any]: ...
    async def fetch_roles(self, guild_id: str) -> list[Role]: ...
    async def fetch_channels(self, guild_id: str) -> list[Channel]: ...
    async def fetch_member(self, guild_id: str, user_id: str) -> GuildMember | None: ...
    async def bot_permissions(self, guild_id: str) -> int: ...
    async def add_role(
        self, guild_id: str, user_id: str, role_id: str, reason: str
    ) -> None: ...
    async def remove_role(
        self, guild_id: str, user_id: str, role_id: str, reason: str
    ) -> None: ...
    async def send_message(self, channel_id: str, content: str) -> str | None: ...
