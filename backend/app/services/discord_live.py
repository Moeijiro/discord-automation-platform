"""Live Discord REST client.

One ``httpx`` client, two credential styles: the user's bearer token for OAuth
identity calls, and the bot token for anything that touches a guild.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import DISCORD_API_BASE, OAUTH_SCOPES, settings
from app.core.permissions import Permission
from app.services.discord_gateway import (
    Channel,
    DiscordError,
    DiscordUser,
    GuildMember,
    OAuthTokens,
    PartialGuild,
    Role,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class LiveDiscordGateway:
    """Implements :class:`~app.services.discord_gateway.DiscordGateway`."""

    is_mock = False

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    # -- transport ---------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        token_type: str = "Bot",
        **kwargs: Any,
    ) -> Any:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"{token_type} {token or settings.discord_bot_token}"
        headers.setdefault("User-Agent", "DiscordAutomationPlatform (portfolio, 1.0)")

        async with httpx.AsyncClient(
            base_url=DISCORD_API_BASE, timeout=self._timeout
        ) as client:
            for attempt in range(MAX_RETRIES):
                response = await client.request(method, path, headers=headers, **kwargs)

                # Discord asks us to back off; honour it once before failing.
                if response.status_code == 429 and attempt + 1 < MAX_RETRIES:
                    retry_after = float(response.headers.get("Retry-After", 1))
                    logger.warning("Rate limited by Discord on %s, waiting %.1fs",
                                   path, retry_after)
                    await asyncio.sleep(min(retry_after, 5))
                    continue

                if response.status_code == 404:
                    raise DiscordError(f"Discord resource not found: {path}", 404)
                if response.status_code == 403:
                    raise DiscordError(
                        "The bot lacks permission for this action in Discord.", 403
                    )
                if response.status_code >= 400:
                    logger.error("Discord %s %s -> %s: %s", method, path,
                                 response.status_code, response.text[:200])
                    raise DiscordError("Discord rejected the request.", 502)

                if response.status_code == 204 or not response.content:
                    return None
                return response.json()

        raise DiscordError("Discord is rate limiting this request.", 429)

    # -- OAuth -------------------------------------------------------------
    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": settings.discord_client_id,
                "redirect_uri": settings.discord_redirect_uri,
                "response_type": "code",
                "scope": " ".join(OAUTH_SCOPES),
                "state": state,
                "prompt": "consent",
            }
        )
        return f"https://discord.com/oauth2/authorize?{query}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        data = {
            "client_id": settings.discord_client_id,
            "client_secret": settings.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.discord_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{DISCORD_API_BASE}/oauth2/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code != 200:
            logger.error("OAuth exchange failed: %s", response.text[:200])
            raise DiscordError("Could not complete the Discord login.", 401)

        payload = response.json()
        return OAuthTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_in=payload.get("expires_in", 604800),
            scope=payload.get("scope", ""),
        )

    async def fetch_current_user(self, access_token: str) -> DiscordUser:
        data = await self._request(
            "GET", "/users/@me", token=access_token, token_type="Bearer"
        )
        return DiscordUser(
            id=data["id"],
            username=data["username"],
            global_name=data.get("global_name"),
            avatar=data.get("avatar"),
        )

    async def fetch_user_guilds(self, access_token: str) -> list[PartialGuild]:
        data = await self._request(
            "GET", "/users/@me/guilds", token=access_token, token_type="Bearer"
        )
        return [
            PartialGuild(
                id=item["id"],
                name=item["name"],
                icon=item.get("icon"),
                owner=item.get("owner", False),
                permissions=str(item.get("permissions", "0")),
            )
            for item in data or []
        ]

    # -- Bot ---------------------------------------------------------------
    async def bot_guild_ids(self) -> set[str]:
        data = await self._request("GET", "/users/@me/guilds")
        return {item["id"] for item in data or []}

    async def fetch_guild(self, guild_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/guilds/{guild_id}", params={"with_counts": "true"}
        )

    async def fetch_roles(self, guild_id: str) -> list[Role]:
        data = await self._request("GET", f"/guilds/{guild_id}/roles")
        return [
            Role(
                id=item["id"],
                name=item["name"],
                color=item.get("color", 0),
                position=item.get("position", 0),
                managed=item.get("managed", False),
                permissions=str(item.get("permissions", "0")),
            )
            for item in data or []
        ]

    async def fetch_channels(self, guild_id: str) -> list[Channel]:
        data = await self._request("GET", f"/guilds/{guild_id}/channels")
        # 0 = text, 5 = announcement: the only ones a welcome message can target.
        return [
            Channel(id=item["id"], name=item["name"], type=item["type"])
            for item in data or []
            if item.get("type") in (0, 5)
        ]

    async def fetch_member(self, guild_id: str, user_id: str) -> GuildMember | None:
        try:
            data = await self._request("GET", f"/guilds/{guild_id}/members/{user_id}")
        except DiscordError as exc:
            if exc.status_code == 404:
                return None
            raise
        return GuildMember(
            id=data["user"]["id"],
            username=data["user"]["username"],
            roles=data.get("roles", []),
            joined_at=data.get("joined_at"),
        )

    async def bot_permissions(self, guild_id: str) -> int:
        """Resolve the bot's effective permissions from its roles in the guild."""
        app_info = await self._request("GET", "/oauth2/applications/@me")
        bot_id = app_info["id"]
        member = await self.fetch_member(guild_id, bot_id)
        if member is None:
            return 0

        roles = {role.id: role for role in await self.fetch_roles(guild_id)}
        guild = await self.fetch_guild(guild_id)
        if guild.get("owner_id") == bot_id:
            return int(Permission.ADMINISTRATOR)

        # @everyone shares the guild's id and applies to every member.
        bits = 0
        for role_id in [guild_id, *member.roles]:
            role = roles.get(role_id)
            if role:
                bits |= int(role.permissions or 0)
        return bits

    async def add_role(
        self, guild_id: str, user_id: str, role_id: str, reason: str
    ) -> None:
        await self._request(
            "PUT",
            f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers={"X-Audit-Log-Reason": reason[:400]},
        )

    async def remove_role(
        self, guild_id: str, user_id: str, role_id: str, reason: str
    ) -> None:
        await self._request(
            "DELETE",
            f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers={"X-Audit-Log-Reason": reason[:400]},
        )

    async def send_message(self, channel_id: str, content: str) -> str | None:
        data = await self._request(
            "POST",
            f"/channels/{channel_id}/messages",
            json={"content": content[:2000], "allowed_mentions": {"parse": ["users"]}},
        )
        return data.get("id") if data else None
