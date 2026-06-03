"""Spring-style `Result<T>` response shape.

The legacy security-server returns every response as
    { "code": 200, "message": "操作成功", "data": <payload> }
and adds an extra `page` field when the payload is paginated. We replicate
the shape exactly so the existing `security-server-ui` doesn't need to be
rewritten.
"""

from __future__ import annotations

from typing import Any


def ok(data: Any = None, *, message: str = "操作成功") -> dict:
    return {"code": 200, "message": message, "data": data}


def paginated(items: list, *, page_num: int, page_size: int, total: int) -> dict:
    """Spring's Result.success(Page<T>) shape: list in data, page meta on the side."""
    return {
        "code": 200,
        "message": "操作成功",
        "data": items,
        "page": {"pageNum": page_num, "pageSize": page_size, "total": total},
    }


def error(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}


class StaffBusinessError(Exception):
    """Equivalent of the Spring `BusinessException`.

    The global exception handler (registered in main.py) converts this to
    a 200 OK response carrying `{code: <code>, message: <msg>, data: null}`
    — that is exactly what the legacy front-end's axios interceptor
    already handles.
    """

    def __init__(self, message: str, *, code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
