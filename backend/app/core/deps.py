"""Common FastAPI dependencies.

This module used to contain a "preview" stub that returned the first user in
the database without validating the bearer token. That stub was an
authentication bypass: any code path importing `get_current_user` from here
would treat anonymous traffic as the first registered user (typically the
superuser). It has been removed.

All endpoints must obtain the current user from `app.api.endpoints.auth`,
which decodes the JWT and looks up the user. The helpers below are thin
wrappers that delegate to that resolver and enforce the most common role
checks, so existing imports keep working.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.api.endpoints.auth import get_current_user as _auth_get_current_user
from app.models.user import User


async def get_current_user(
    user: User = Depends(_auth_get_current_user),
) -> User:
    """Return the authenticated user resolved from the JWT bearer token."""
    return user


async def get_current_active_user(
    user: User = Depends(_auth_get_current_user),
) -> User:
    if not getattr(user, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


async def get_current_staff_user(
    user: User = Depends(get_current_active_user),
) -> User:
    if not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required",
        )
    return user


async def get_current_superuser(
    user: User = Depends(get_current_active_user),
) -> User:
    if not getattr(user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return user
