"""Audit-log helpers for sensitive (mostly billing-related) operations.

These helpers intentionally swallow exceptions: a failed audit insert must
not block the underlying business action — but the action SHOULD still be
auditable on the happy path. Endpoints call ``record_audit`` after the
business-logic commit so a failure here only loses the trail entry, never
the financial change itself.

The detail payload is serialized to JSON when possible, otherwise stringified.
Keep entries small and structured so they can be queried later.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _format_detail(detail: Any) -> Optional[str]:
    if detail is None:
        return None
    if isinstance(detail, str):
        return detail[:4000]
    try:
        return json.dumps(detail, ensure_ascii=False, default=str)[:4000]
    except (TypeError, ValueError):
        return str(detail)[:4000]


async def record_audit(
    db: AsyncSession,
    *,
    user_id: Optional[int],
    action: str,
    detail: Any = None,
) -> None:
    """Insert an AuditLog row. Errors are swallowed."""
    try:
        db.add(AuditLog(user_id=user_id, action=action, detail=_format_detail(detail)))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()


def diff_payload(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    fields: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return a {field: {"from": x, "to": y}} dict for changed fields only."""
    keys = list(fields) if fields is not None else sorted(set(before) | set(after))
    changes: dict[str, Any] = {}
    for key in keys:
        old = before.get(key)
        new = after.get(key)
        if old != new:
            changes[key] = {"from": old, "to": new}
    return changes
