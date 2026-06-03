"""
Shared database helpers for app runtime and ad-hoc maintenance scripts.
"""

from __future__ import annotations

from urllib.parse import quote

from app.core.config import settings


def get_mysql_connection_kwargs(*, charset: str = "utf8mb4") -> dict[str, object]:
    """Return PyMySQL-compatible connection kwargs based on backend settings."""
    return {
        "host": settings.MYSQL_SERVER,
        "user": settings.MYSQL_USER,
        "password": settings.MYSQL_PASSWORD,
        "database": settings.MYSQL_DB,
        "port": settings.MYSQL_PORT,
        "charset": charset,
    }


def get_sync_database_url() -> str:
    """Build a sync SQLAlchemy URL that mirrors the backend's MySQL settings."""
    user = quote(settings.MYSQL_USER, safe="")
    password = quote(settings.MYSQL_PASSWORD, safe="")
    database = quote(settings.MYSQL_DB, safe="")
    return (
        f"mysql+pymysql://{user}:{password}@"
        f"{settings.MYSQL_SERVER}:{settings.MYSQL_PORT}/{database}"
    )
