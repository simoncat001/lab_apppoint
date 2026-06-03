"""Shared staff DTOs: pagination params + common base."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class StaffSchema(BaseModel):
    """Base config for staff DTOs — camelCase JSON, snake_case Python."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PageParam(StaffSchema):
    page_num: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=200)
    enable: bool = True


class BasePageRequest(StaffSchema):
    page_param: Optional[PageParam] = None
    keyword: Optional[str] = None

    def normalized_page(self) -> tuple[int, int, bool]:
        """Return (page_num, page_size, enabled) using Spring defaults."""
        pp = self.page_param or PageParam()
        return int(pp.page_num or 1), int(pp.page_size or 10), bool(pp.enable if pp.enable is not None else True)
