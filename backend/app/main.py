"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, automation, guilds, system, users
from app.core.config import settings
from app.db.session import init_db
from app.services.automation import AutomationError
from app.services.discord_gateway import DiscordError
from app.services.gateway_factory import get_gateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

DESCRIPTION = """
Manage Discord automation for a server from one dashboard.

* **Authentication** - Discord OAuth2; the browser only ever holds an HttpOnly
  session cookie, OAuth tokens stay encrypted on the server.
* **Permissions** - every guild route checks the caller's Discord permissions
  *and* the bot's before anything is changed.
* **Demo mode** - when no Discord credentials are configured the API serves
  deterministic mock structure and says so in `GET /api/health`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    gateway = get_gateway()
    logger.info(
        "Discord Automation Platform ready (environment=%s, mode=%s)",
        settings.environment,
        "demo" if gateway.is_mock else "live",
    )
    yield


app = FastAPI(
    title="Discord Automation Platform",
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # the session cookie must ride along
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Signature"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # noqa: ANN001, ANN201
    """Conservative defaults; the API serves JSON, never HTML documents."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(DiscordError)
async def discord_error_handler(_: Request, exc: DiscordError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.exception_handler(AutomationError)
async def automation_error_handler(_: Request, exc: AutomationError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(guilds.router)
app.include_router(automation.router)

from app.api.routes import webhooks  # noqa: E402  (kept last: unauthenticated)

app.include_router(webhooks.router)


@app.get("/", include_in_schema=False)
def index() -> JSONResponse:
    return JSONResponse(
        {
            "service": "discord-automation-platform",
            "docs": "/docs",
            "health": "/api/health",
        },
        status_code=status.HTTP_200_OK,
    )
