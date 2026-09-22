"""The Discord gateway bot.

It is a thin event listener on purpose: when a member joins, it looks up that
guild's configuration and calls the *same* automation service the REST API
calls. There is one implementation of "what happens on join", not two.

    Discord event -> bot -> app.services.automation -> Discord API + audit log
"""

from __future__ import annotations

import logging

import discord

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.models import Guild
from app.services import automation
from app.services import guilds as guild_service
from app.services.gateway_factory import get_gateway

logger = logging.getLogger("bot")


def build_intents() -> discord.Intents:
    """Only what the automations need.

    SERVER MEMBERS is a privileged intent -- enable it in the Discord
    developer portal or on_member_join never fires.
    """
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    return intents


class AutomationBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=build_intents())
        self.gateway = get_gateway()

    async def on_ready(self) -> None:
        logger.info("Connected as %s in %d guild(s)", self.user, len(self.guilds))
        self._mark_presence()

    def _mark_presence(self) -> None:
        """Keep Guild.bot_present in step with reality on every reconnect."""
        live_ids = {str(guild.id) for guild in self.guilds}
        with SessionLocal() as db:
            for guild in db.query(Guild).all():
                desired = guild.discord_id in live_ids
                if guild.bot_present != desired:
                    guild.bot_present = desired
            db.commit()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info("Added to guild %s (%s)", guild.name, guild.id)
        self._mark_presence()

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info("Removed from guild %s (%s)", guild.name, guild.id)
        self._mark_presence()

    async def on_member_join(self, member: discord.Member) -> None:
        """Welcome message and join autorole, driven by stored settings."""
        with SessionLocal() as db:
            guild = guild_service.get_guild_by_discord_id(db, str(member.guild.id))
            if guild is None:
                # Nobody has logged into the dashboard for this guild yet.
                logger.debug("Ignoring join in unconfigured guild %s", member.guild.id)
                return

            guild.bot_present = True
            db.commit()

            try:
                await automation.handle_member_join(
                    db,
                    guild=guild,
                    settings=guild_service.get_settings(db, guild),
                    gateway=self.gateway,
                    member_id=str(member.id),
                    username=member.name,
                    member_count=member.guild.member_count or 0,
                )
            except Exception:  # noqa: BLE001 - one bad join must not kill the bot
                logger.exception("Join automation failed for guild %s", guild.discord_id)


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    if not settings.discord_bot_token:
        raise SystemExit(
            "DISCORD_BOT_TOKEN is not set.\n"
            "The dashboard runs without it in demo mode, but the gateway bot "
            "needs a real token -- add one to backend/.env to run it."
        )
    init_db()
    AutomationBot().run(settings.discord_bot_token, log_handler=None)
