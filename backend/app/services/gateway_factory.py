"""Chooses the Discord implementation once, at import time."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings
from app.services.discord_gateway import DiscordGateway
from app.services.discord_live import LiveDiscordGateway
from app.services.discord_mock import MockDiscordGateway

logger = logging.getLogger(__name__)


@lru_cache
def get_gateway() -> DiscordGateway:
    """Live client when credentials exist and demo mode is off, else the mock."""
    if settings.live_mode:
        logger.info("Discord gateway: LIVE")
        return LiveDiscordGateway()

    reason = "DEMO_MODE=true" if settings.demo_mode else "no Discord credentials"
    logger.warning("Discord gateway: DEMO (%s) -- no calls will reach Discord", reason)
    return MockDiscordGateway()


def current_mode() -> str:
    return "live" if get_gateway().is_mock is False else "demo"
