"""Staff (security-server) password + JWT helpers.

Compatibility notes:
- The legacy Spring service stored passwords as plain MD5 hex digests
  (`SecureUtil.md5`). We MUST keep that scheme so existing staff_user rows
  remain authenticatable. The hash is too weak for new systems, but the
  upgrade path is "verify with md5 on login, then re-hash with bcrypt and
  swap the column type" — left as a future TODO.
- JWT shares nemo's SECRET_KEY (and HS256). The `sub` claim is namespaced
  as `staff:<username>` so the nemo `get_current_user` never confuses a
  staff token with a nemo-local token.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings

STAFF_SUBJECT_PREFIX = "staff:"


def md5_hash(raw_password: str) -> str:
    """Spring's `SecureUtil.md5(raw)` — lowercase hex digest, no salt."""
    return hashlib.md5(raw_password.encode("utf-8")).hexdigest()


def md5_matches(raw_password: str, stored_hash: str) -> bool:
    if not raw_password or not stored_hash:
        return False
    return md5_hash(raw_password) == stored_hash.lower()


def create_staff_token(username: str, *, extra: Optional[dict[str, Any]] = None) -> str:
    """Issue a JWT for a staff user.

    The token expiry mirrors nemo's ACCESS_TOKEN_EXPIRE_MINUTES so admins
    don't have to remember two different durations.
    """
    payload: dict[str, Any] = {
        "sub": f"{STAFF_SUBJECT_PREFIX}{username}",
        "scope": "staff",
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_staff_token(token: str) -> dict[str, Any]:
    """Decode any token; caller is responsible for checking the staff prefix."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError(str(exc)) from exc


def extract_staff_username(token: str) -> Optional[str]:
    """Return the staff username if `token` is a staff token, else None."""
    try:
        payload = decode_staff_token(token)
    except ValueError:
        return None
    sub = payload.get("sub") or ""
    if not isinstance(sub, str) or not sub.startswith(STAFF_SUBJECT_PREFIX):
        return None
    return sub[len(STAFF_SUBJECT_PREFIX):] or None
