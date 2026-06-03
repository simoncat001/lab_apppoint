"""Internal-employee auth service (legacy name preserved).

Historically this called the standalone Spring `security-server` over HTTP.
Now that the staff data lives in the same database (the `staff_*` tables)
and the staff endpoints are served in-process by `app.api.endpoints.staff.*`,
this module is just a thin facade that:

- exposes the same public API as before (so all call sites keep working);
- authenticates against `staff_user` directly;
- signs the same Spring-style token via `app.core.staff_security`;
- keeps the per-user token cache that `project_context` still consults.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.staff_security import create_staff_token, md5_matches
from app.db.session import AsyncSessionLocal
from app.models.staff import StaffUser


class SecurityServerAuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _serialize_user(user: StaffUser) -> dict[str, Any]:
    """Mirror Spring's User entity shape (camelCase keys, password stripped)."""
    return {
        "id": int(user.id) if user.id is not None else None,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "jobNumber": user.job_number,
        "status": user.status,
        "createdTime": user.created_time.isoformat() if user.created_time else None,
        "updatedTime": user.updated_time.isoformat() if user.updated_time else None,
    }


class SecurityServerAuthService:
    """Facade over the in-process staff auth module.

    The class-level token cache used to hold tokens issued by the remote
    Spring service; we keep it because `project_context` and a few
    endpoints still consult it. With in-process auth the cache is purely
    optional (we can decode the JWT to recover the username), but it
    speeds up the hot path and keeps existing call sites unchanged.
    """

    _user_token_cache: dict[str, str] = {}

    # ------------------------------------------------------- token cache
    @staticmethod
    def _normalize_cache_key(username: str) -> str:
        return (username or "").strip().lower()

    @staticmethod
    def cache_user_token(username: str, token: str) -> None:
        key = SecurityServerAuthService._normalize_cache_key(username)
        if not key:
            return
        value = (token or "").strip()
        if not value:
            SecurityServerAuthService._user_token_cache.pop(key, None)
            return
        SecurityServerAuthService._user_token_cache[key] = value

    @staticmethod
    def get_cached_user_token(username: str) -> str | None:
        key = SecurityServerAuthService._normalize_cache_key(username)
        if not key:
            return None
        value = SecurityServerAuthService._user_token_cache.get(key)
        if not value:
            return None
        return value.strip() or None

    @staticmethod
    def clear_cached_user_token(username: str) -> None:
        key = SecurityServerAuthService._normalize_cache_key(username)
        if key:
            SecurityServerAuthService._user_token_cache.pop(key, None)

    # ----------------------------------------------------------- feature
    @staticmethod
    def is_enabled() -> bool:
        # Staff endpoints are always in-process now. The legacy config flag
        # still lets ops disable the integration entirely for emergencies.
        return bool(settings.SECURITY_SERVER_ENABLED)

    # ------------------------------------------------------------- login
    @staticmethod
    async def login(username: str, password: str) -> dict[str, Any]:
        """Authenticate against `staff_user` and return Spring's data block.

        Response shape matches Spring's `Result<LoginResponse>.data`:
            { "token": "...", "userInfo": { ...user fields... } }
        """
        if not SecurityServerAuthService.is_enabled():
            raise SecurityServerAuthError(
                "Security server authentication is not enabled",
                status_code=503,
            )

        username_normalized = (username or "").strip()
        if not username_normalized or not password:
            raise SecurityServerAuthError("Incorrect username or password", status_code=401)

        try:
            async with AsyncSessionLocal() as session:
                user = (
                    await session.execute(
                        select(StaffUser).where(StaffUser.username == username_normalized)
                    )
                ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise SecurityServerAuthError(
                "Security server (staff DB) is unavailable",
                status_code=502,
            ) from exc

        if user is None:
            raise SecurityServerAuthError("Incorrect username or password", status_code=401)
        if int(user.status or 0) == 0:
            raise SecurityServerAuthError(
                "Account is not yet approved or has been disabled",
                status_code=403,
            )
        if not md5_matches(password, user.password or ""):
            raise SecurityServerAuthError("Incorrect username or password", status_code=401)

        token = create_staff_token(user.username)
        SecurityServerAuthService.cache_user_token(user.username, token)

        return {
            "token": token,
            "userInfo": _serialize_user(user),
        }
