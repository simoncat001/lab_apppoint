"""
User API endpoints
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import User, UserCreate, UserUpdate, PasswordChangeRequest
from app.services.user_service import UserService
from app.api.endpoints.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return current_user


@router.put("/me", response_model=User)
async def update_users_me(
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新当前登录用户信息"""
    # 普通用户只能更新非特权字段
    update_data = user_in.model_dump(exclude_unset=True)
    forbidden_fields = {
        "is_active",
        "is_verified",
        "is_staff",
        "is_superuser",
        "auth_source",
        "priority_reservation",
        "special_course_access",
        "managed_tool_ids",
    }
    if any(field in update_data for field in forbidden_fields):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    user = await service.update_user(current_user.id, user_in)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码"""
    service = UserService(db)
    user = await service.get_user_by_username(current_user.username)
    if user and (getattr(user, "auth_source", "local") or "local") == "security_server":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internal employee accounts are managed by the security service. Please change password there.",
        )
    if not user or not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password incorrect")
    await service.update_password(current_user.id, payload.new_password)
    return {"message": "Password updated"}


@router.get("/", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户列表"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    users = await service.get_users(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个用户"""
    if not (current_user.is_staff or current_user.is_superuser) and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新用户"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    user_in.auth_source = "local"
    
    # 检查用户名是否已存在
    existing_user = await service.get_user_by_username(user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    existing_email = await service.get_user_by_email(user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await service.create_user(user_in)
    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户"""
    is_admin = current_user.is_staff or current_user.is_superuser

    if not is_admin and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Non-admin users cannot change privileged fields.
    if not is_admin:
        update_data = user_in.model_dump(exclude_unset=True)
        forbidden_fields = {
            "is_active",
            "is_verified",
            "is_staff",
            "is_superuser",
            "auth_source",
            "priority_reservation",
            "special_course_access",
            "managed_tool_ids",
        }
        if any(field in update_data for field in forbidden_fields):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    user = await service.update_user(user_id, user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除用户"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    service = UserService(db)
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return None
