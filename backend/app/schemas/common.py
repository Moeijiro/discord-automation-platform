"""Shared field types and response envelopes."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

SNOWFLAKE_RE = re.compile(r"^\d{17,20}$")


def _validate_snowflake(value: object) -> object:
    """Discord ids are 17-20 digit strings; reject anything else up front."""
    if value is None or value == "":
        return None
    text = str(value)
    if not SNOWFLAKE_RE.match(text):
        raise ValueError("must be a Discord ID (17-20 digits)")
    return text


Snowflake = Annotated[str, BeforeValidator(_validate_snowflake)]
OptionalSnowflake = Annotated[str | None, BeforeValidator(_validate_snowflake)]


class ErrorResponse(BaseModel):
    """The shape every error in this API takes."""

    detail: str = Field(examples=["You do not manage this server."])


class ModeInfo(BaseModel):
    """Tells the frontend whether it is looking at live or demo data."""

    mode: Literal["live", "demo"]
    demo: bool
    discord_configured: bool
