"""The authenticated user."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/me", response_model=UserOut, summary="Current user")
def read_me(user: User = Depends(get_current_user)) -> User:
    return user
