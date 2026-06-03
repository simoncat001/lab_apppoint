from fastapi import HTTPException, status

from app.models.user import User


def is_global_tool_admin(user: User | None) -> bool:
    if user is None:
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    if not bool(getattr(user, "is_staff", False)):
        return False
    return not bool(getattr(user, "managed_tool_ids_list", []) or [])


def can_manage_tool(user: User | None, tool_id: int | None) -> bool:
    if user is None or tool_id is None:
        return False
    if is_global_tool_admin(user):
        return True
    if not bool(getattr(user, "is_staff", False)):
        return False
    return int(tool_id) in set(getattr(user, "managed_tool_ids_list", []) or [])


def require_tool_manager(user: User | None, tool_id: int | None) -> None:
    if not can_manage_tool(user, tool_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global staff or this tool's administrator can perform this action",
        )
