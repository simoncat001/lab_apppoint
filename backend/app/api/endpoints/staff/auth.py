"""Staff auth endpoints — port of AuthController."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.staff_security import create_staff_token
from app.db.session import get_db
from app.schemas.staff.user import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    StaffUserResponse,
)
from app.services.staff.result import StaffBusinessError, ok
from app.services.staff.user_service import StaffUserService

router = APIRouter()


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = StaffUserService(db)
    user = await service.get_by_username(payload.username)
    if user is None:
        raise StaffBusinessError("用户名或密码错误", code=401)
    if int(user.status or 0) == 0:
        raise StaffBusinessError("账户尚未审核或已被禁用", code=403)
    if not await service.verify_password(user, payload.password):
        raise StaffBusinessError("用户名或密码错误", code=401)

    token = create_staff_token(user.username)
    # The legacy frontend reads `data.token` and `data.userInfo` (Spring's
    # LoginResponse). We hide the password before serialising.
    user.password = None
    return ok(
        LoginResponse(
            token=token,
            userInfo=StaffUserResponse.model_validate(user),
        ).model_dump(by_alias=True, exclude_none=True)
    )


@router.post("/register")
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = StaffUserService(db)
    await service.register(
        username=payload.username,
        password=payload.password,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
    )
    return ok(True)


@router.post("/logout")
async def logout():
    # JWT is stateless; the frontend just drops the token. We return the
    # same shape Spring did for compatibility.
    return ok(True)
