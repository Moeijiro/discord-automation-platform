"""Discord OAuth2 login.

Flow:

    GET  /api/auth/login     -> signed state cookie + redirect to Discord
    GET  /api/auth/callback  -> verify state, exchange code, issue session
    POST /api/auth/logout    -> clear the session cookie

The access token never leaves the backend: it is encrypted, stored, and used
server side. The browser only ever holds an HttpOnly session cookie.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import gateway_dependency, get_current_user
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.core.security import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_session_token,
    encrypt_token,
    generate_oauth_state,
    verify_oauth_state,
)
from app.db.session import get_db
from app.models import User
from app.schemas.common import ModeInfo
from app.schemas.user import UserOut
from app.services import guilds as guild_service
from app.services.discord_gateway import DiscordError, DiscordGateway

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

login_limit = RateLimiter(times=10, seconds=60, scope="auth")


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.get("/mode", response_model=ModeInfo, summary="Live or demo data?")
def auth_mode(gateway: DiscordGateway = Depends(gateway_dependency)) -> ModeInfo:
    """Public: lets the login screen say which mode it is about to use."""
    return ModeInfo(
        mode="demo" if gateway.is_mock else "live",
        demo=gateway.is_mock,
        discord_configured=settings.discord_configured,
    )


@router.get("/login", summary="Start the Discord OAuth2 flow")
def login(
    _: None = Depends(login_limit),
    gateway: DiscordGateway = Depends(gateway_dependency),
) -> RedirectResponse:
    state = generate_oauth_state()
    response = RedirectResponse(gateway.authorize_url(state), status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )
    return response


@router.get("/callback", summary="Discord redirects here with the code")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(login_limit),
) -> RedirectResponse:
    def failure(reason: str) -> RedirectResponse:
        logger.warning("OAuth callback rejected: %s", reason)
        redirect = RedirectResponse(f"{settings.frontend_url}/login?error={reason}", 302)
        redirect.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth")
        return redirect

    if error:
        return failure("access_denied")
    if not code:
        return failure("missing_code")
    # The state cookie is what stops a third party from replaying a code here.
    if not verify_oauth_state(state, request.cookies.get(OAUTH_STATE_COOKIE_NAME)):
        return failure("invalid_state")

    try:
        tokens = await gateway.exchange_code(code)
        profile = await gateway.fetch_current_user(tokens.access_token)
        partials = await gateway.fetch_user_guilds(tokens.access_token)
        bot_guild_ids = await gateway.bot_guild_ids()
    except DiscordError as exc:
        logger.error("OAuth exchange failed: %s", exc.message)
        return failure("discord_error")

    user = db.execute(
        select(User).where(User.discord_id == profile.id)
    ).scalar_one_or_none()
    if user is None:
        user = User(discord_id=profile.id, username=profile.username)
        db.add(user)

    user.username = profile.username
    user.global_name = profile.global_name
    user.avatar = profile.avatar
    user.access_token_encrypted = encrypt_token(tokens.access_token)
    user.refresh_token_encrypted = encrypt_token(tokens.refresh_token)
    user.token_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
    ).isoformat()
    db.commit()
    db.refresh(user)

    guild_service.sync_user_guilds(db, user, partials, bot_guild_ids)

    response = RedirectResponse(f"{settings.frontend_url}/dashboard", status_code=302)
    _set_session_cookie(response, create_session_token(user.id, user.discord_id))
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth")
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="End session")
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh-guilds", response_model=UserOut, summary="Re-sync guild access")
async def refresh_guilds(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway: DiscordGateway = Depends(gateway_dependency),
    _: None = Depends(RateLimiter(times=5, seconds=60, scope="refresh")),
) -> User:
    """Pull the user's guild list from Discord again, on demand."""
    from app.core.security import decrypt_token

    access_token = decrypt_token(user.access_token_encrypted)
    if not access_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Session expired, please sign in again."
        )
    try:
        partials = await gateway.fetch_user_guilds(access_token)
        bot_guild_ids = await gateway.bot_guild_ids()
    except DiscordError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    guild_service.sync_user_guilds(db, user, partials, bot_guild_ids)
    return user
