"""Discord permission bitfield helpers.

Only the flags this platform actually checks are modelled -- the dashboard
never needs the full set, and a short list is easier to audit.
"""

from __future__ import annotations

from enum import IntFlag


class Permission(IntFlag):
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_GUILD = 1 << 5
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    MANAGE_ROLES = 1 << 28


def parse(raw: str | int | None) -> Permission:
    """Discord sends the bitfield as a string; treat anything unparsable as none."""
    try:
        return Permission(int(raw or 0))
    except (TypeError, ValueError):
        return Permission(0)


def has(raw: str | int | None, flag: Permission) -> bool:
    """ADMINISTRATOR implies every other permission, exactly as Discord does."""
    bits = parse(raw)
    return bool(bits & Permission.ADMINISTRATOR or bits & flag)


def can_manage_guild(raw: str | int | None, *, is_owner: bool = False) -> bool:
    """Who may see and change a guild's automation settings."""
    return is_owner or has(raw, Permission.MANAGE_GUILD)


def describe(raw: str | int | None) -> list[str]:
    """Human-readable flag names, for the API and the audit trail."""
    return [flag.name for flag in Permission if flag.name and parse(raw) & flag]
