"""Application configuration.

Every setting is read from the environment (or a local ``.env`` file) so the
same image can run in development, demo and production without code changes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_CDN_BASE = "https://cdn.discordapp.com"
OAUTH_SCOPES = ("identify", "guilds")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Runtime ---------------------------------------------------------
    environment: Literal["development", "production"] = "development"
    demo_mode: bool = True

    # --- Discord application --------------------------------------------
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_bot_token: str = ""
    discord_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # --- Database --------------------------------------------------------
    database_url: str = "sqlite:///./discord_automation.db"

    # --- Security --------------------------------------------------------
    session_secret: str = Field(default="dev-only-insecure-secret", min_length=8)
    session_ttl_minutes: int = Field(default=60 * 24 * 7, ge=5)
    cookie_secure: bool = False
    webhook_secret: str = "dev-only-insecure-webhook-secret"

    # --- Frontend --------------------------------------------------------
    frontend_url: str = "http://localhost:5173"

    @field_validator("frontend_url", "discord_redirect_uri")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        """Fail fast instead of quietly serving fake data or a known secret."""
        if self.environment == "production":
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false when ENVIRONMENT=production")
            if "insecure" in self.session_secret or len(self.session_secret) < 32:
                raise ValueError("SESSION_SECRET must be a strong value in production")
            if not self.discord_configured:
                raise ValueError(
                    "DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET and DISCORD_BOT_TOKEN "
                    "are required when ENVIRONMENT=production"
                )
        return self

    @property
    def discord_configured(self) -> bool:
        """True when real Discord credentials are present."""
        return bool(
            self.discord_client_id
            and self.discord_client_secret
            and self.discord_bot_token
        )

    @property
    def live_mode(self) -> bool:
        """True when the platform talks to the real Discord API."""
        return self.discord_configured and not self.demo_mode

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
