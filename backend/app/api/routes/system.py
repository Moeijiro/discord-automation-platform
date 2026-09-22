"""Health and service metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import gateway_dependency
from app.core.config import settings
from app.db.session import get_db
from app.services.discord_gateway import DiscordGateway

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", summary="Liveness and mode")
def health(
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # pragma: no cover - only on a broken DB
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "mode": "demo" if gateway.is_mock else "live",
        "database": "ok" if database_ok else "unavailable",
        "environment": settings.environment,
        "discord_configured": settings.discord_configured,
    }
