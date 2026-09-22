"""Demo gateway: deterministic data, no network, no Discord application.

It exists so the dashboard can be reviewed (and screenshotted) without a bot
token. Everything it returns is fabricated *structure* -- guild names, roles,
channels -- never fabricated activity: the audit trail a reviewer sees is the
real record of what they clicked in this session, and the API marks every
response ``"mode": "demo"``.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from app.core.config import settings
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

DEMO_USER = DiscordUser(
    id="900000000000000001", username="demo.admin", global_name="Demo Admin"
)

_MANAGE = str(int(Permission.MANAGE_GUILD | Permission.MANAGE_ROLES))
_ADMIN = str(int(Permission.ADMINISTRATOR))

DEMO_GUILDS: list[PartialGuild] = [
    PartialGuild("100000000000000001", "Nebula Labs", None, True, _ADMIN),
    PartialGuild("100000000000000002", "Indie Game Collective", None, False, _MANAGE),
    # Listed by Discord but not manageable -- proves the permission gate.
    PartialGuild("100000000000000003", "Study Hall", None, False, "0"),
]

_ROLES: dict[str, list[Role]] = {
    "100000000000000001": [
        Role("100000000000000001", "@everyone", 0, 0, permissions="104189505"),
        Role("200000000000000011", "Verified", 0x3BA55D, 1),
        Role("200000000000000012", "Contributor", 0x5865F2, 2),
        Role("200000000000000013", "Maintainer", 0xEB459E, 3),
        Role("200000000000000014", "Automation Bot", 0x99AAB5, 4, managed=True,
             permissions=str(int(Permission.MANAGE_ROLES | Permission.SEND_MESSAGES
                                 | Permission.VIEW_CHANNEL))),
    ],
    "100000000000000002": [
        Role("100000000000000002", "@everyone", 0, 0, permissions="104189505"),
        Role("200000000000000021", "Verified", 0x3BA55D, 1),
        Role("200000000000000022", "Playtester", 0xFAA61A, 2),
        Role("200000000000000023", "Automation Bot", 0x99AAB5, 3, managed=True,
             permissions=str(int(Permission.MANAGE_ROLES | Permission.SEND_MESSAGES
                                 | Permission.VIEW_CHANNEL))),
    ],
}

_CHANNELS: dict[str, list[Channel]] = {
    "100000000000000001": [
        Channel("300000000000000011", "welcome"),
        Channel("300000000000000012", "general"),
        Channel("300000000000000013", "automation-log"),
    ],
    "100000000000000002": [
        Channel("300000000000000021", "lobby"),
        Channel("300000000000000022", "playtest-builds"),
    ],
}

_MEMBER_COUNTS = {"100000000000000001": 1284, "100000000000000002": 342}
# The bot is in the first two guilds only.
_BOT_GUILDS = {"100000000000000001", "100000000000000002"}


class MockDiscordGateway:
    """Implements :class:`~app.services.discord_gateway.DiscordGateway`."""

    is_mock = True

    def __init__(self) -> None:
        # Role changes made during the session, so the UI reflects the click.
        self._assignments: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.sent_messages: list[tuple[str, str]] = []

    # -- OAuth -------------------------------------------------------------
    def authorize_url(self, state: str) -> str:
        """Skip Discord entirely and bounce straight back to the callback."""
        return f"{settings.discord_redirect_uri}?{urlencode({'code': 'demo', 'state': state})}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        return OAuthTokens(access_token="demo-access-token", refresh_token="demo-refresh")

    async def fetch_current_user(self, access_token: str) -> DiscordUser:
        return DEMO_USER

    async def fetch_user_guilds(self, access_token: str) -> list[PartialGuild]:
        return list(DEMO_GUILDS)

    # -- Bot ---------------------------------------------------------------
    async def bot_guild_ids(self) -> set[str]:
        return set(_BOT_GUILDS)

    async def fetch_guild(self, guild_id: str) -> dict[str, Any]:
        guild = next((g for g in DEMO_GUILDS if g.id == guild_id), None)
        if guild is None:
            raise DiscordError("Unknown guild", 404)
        return {
            "id": guild.id,
            "name": guild.name,
            "icon": guild.icon,
            "owner_id": DEMO_USER.id if guild.owner else "0",
            "approximate_member_count": _MEMBER_COUNTS.get(guild_id, 0),
            "approximate_presence_count": _MEMBER_COUNTS.get(guild_id, 0) // 6,
        }

    async def fetch_roles(self, guild_id: str) -> list[Role]:
        return list(_ROLES.get(guild_id, []))

    async def fetch_channels(self, guild_id: str) -> list[Channel]:
        return list(_CHANNELS.get(guild_id, []))

    async def fetch_member(self, guild_id: str, user_id: str) -> GuildMember | None:
        if guild_id not in _BOT_GUILDS:
            return None
        return GuildMember(
            id=user_id,
            username=DEMO_USER.username if user_id == DEMO_USER.id else f"member-{user_id[-4:]}",
            roles=sorted(self._assignments[(guild_id, user_id)]),
            joined_at=datetime.now(timezone.utc).isoformat(),
        )

    async def bot_permissions(self, guild_id: str) -> int:
        if guild_id not in _BOT_GUILDS:
            return 0
        return int(
            Permission.MANAGE_ROLES | Permission.SEND_MESSAGES | Permission.VIEW_CHANNEL
        )

    async def add_role(self, guild_id: str, user_id: str, role_id: str, reason: str) -> None:
        self._require_known_role(guild_id, role_id)
        self._assignments[(guild_id, user_id)].add(role_id)

    async def remove_role(self, guild_id: str, user_id: str, role_id: str, reason: str) -> None:
        self._require_known_role(guild_id, role_id)
        self._assignments[(guild_id, user_id)].discard(role_id)

    async def send_message(self, channel_id: str, content: str) -> str | None:
        self.sent_messages.append((channel_id, content))
        return f"4000000000000000{len(self.sent_messages):02d}"

    def _require_known_role(self, guild_id: str, role_id: str) -> None:
        if not any(role.id == role_id for role in _ROLES.get(guild_id, [])):
            raise DiscordError("Unknown role for this guild", 404)
