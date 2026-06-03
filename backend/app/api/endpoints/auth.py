"""
Authentication endpoints
"""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.schemas.user import Token, User, UserCreate
from app.schemas.verification import VerificationCodeRequest, VerificationCodeResponse
from app.services.security_server_auth_service import (
    SecurityServerAuthError,
    SecurityServerAuthService,
)
from app.services.security_server_project_service import SecurityServerProjectService
from app.services.user_service import UserService
from app.services.verification_service import VerificationService, VerificationServiceError
from app.models.audit_log import AuditLog
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def _is_external_user_session(user: User | None) -> bool:
    """Treat local non-superuser accounts as external users."""
    if not user:
        return False
    auth_source = (getattr(user, "auth_source", None) or "local").lower()
    return auth_source == "local" and not bool(getattr(user, "is_superuser", False))


def _apply_external_user_scope(user: User | None) -> User | None:
    """Prevent external users from gaining management capabilities via local flags."""
    if not user:
        return user
    if _is_external_user_session(user):
        user.is_staff = False
        # External users should not receive any tool-management hints in the session payload.
        user.managed_tool_ids = None
    return user


async def _apply_security_server_scope(
    db: AsyncSession,
    user: User | None,
) -> User | None:
    if not user:
        return user
    auth_source = (getattr(user, "auth_source", None) or "local").lower()
    if auth_source != "security_server":
        return user

    snapshot = await SecurityServerProjectService.get_permission_snapshot_for_username_from_db(
        db,
        username=str(getattr(user, "username", "") or "").strip(),
    )
    user.is_superuser = snapshot.is_super_admin
    user.is_staff = snapshot.is_admin
    user.is_verified = True
    return user


async def _authenticate_local_password_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    reject_security_sourced: bool,
):
    service = UserService(db)
    user = await service.get_user_by_username(username)
    if not user:
        return None

    auth_source = (getattr(user, "auth_source", None) or "local").lower()
    if reject_security_sourced and auth_source == "security_server":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is managed by the internal security service. Please use internal employee login.",
        )

    if not verify_password(password, user.hashed_password):
        return None
    return user


async def _authenticate_security_server_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
):
    try:
        login_data = await SecurityServerAuthService.login(username, password)
    except SecurityServerAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    user_info = login_data.get("userInfo") or {}
    service = UserService(db)
    try:
        user = await service.get_or_create_security_server_user(user_info)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid user payload from security server",
        ) from exc

    return user


async def _resolve_password_login_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    auth_source: Optional[str] = None,
):
    source = (auth_source or "auto").strip().lower()
    if source not in {"auto", "internal", "external"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid auth_source, must be one of: auto, internal, external",
        )

    if source == "internal":
        return await _authenticate_security_server_user(db, username=username, password=password)

    if source == "external":
        user = await _authenticate_local_password_user(
            db,
            username=username,
            password=password,
            reject_security_sourced=True,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # auto mode: route by local profile if present, otherwise fallback to security-server
    service = UserService(db)
    local_user = await service.get_user_by_username(username)
    if local_user:
        local_source = (getattr(local_user, "auth_source", None) or "local").lower()
        if local_source == "security_server":
            return await _authenticate_security_server_user(db, username=username, password=password)
        if verify_password(password, local_user.hashed_password):
            return local_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if SecurityServerAuthService.is_enabled():
        return await _authenticate_security_server_user(db, username=username, password=password)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _issue_login_token_response(
    db: AsyncSession,
    *,
    user,
    request: Request | None,
) -> Token:
    service = UserService(db)
    user = _apply_external_user_scope(user)
    user = await _apply_security_server_scope(db, user)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    await service.update_last_login(user.id)

    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    detail = f"ip={client_ip}; ua={user_agent}"
    try:
        db.add(AuditLog(user_id=user.id, action="LOGIN", detail=detail))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()

    return Token(access_token=access_token, token_type="bearer", user=user)



async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    service = UserService(db)
    user = await service.get_user_by_username(username)
    if user is None:
        raise credentials_exception

    user = _apply_external_user_scope(user)
    user = await _apply_security_server_scope(db, user)
    return user


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    注册新用户
    """
    service = UserService(db)

    # Extract fields for user creation
    try:
        user_in = UserCreate.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user payload")

    # 检查用户名是否存在
    existing_user = await service.get_user_by_username(user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否存在
    existing_email = await service.get_user_by_email(user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if user_in.phone_number:
        existing_phone = await service.get_user_by_phone(user_in.phone_number)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered",
            )
    
    # 新注册用户默认未激活，需要管理员审核
    user_in.is_active = False
    user_in.auth_source = "local"
    user_in.priority_reservation = False
    user_in.special_course_access = False
    user_in.managed_tool_ids = None
    
    user = await service.create_user(user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """用户登录"""
    auth_source = request.headers.get("x-auth-source") if request else None
    user = await _resolve_password_login_user(
        db,
        username=form_data.username,
        password=form_data.password,
        auth_source=auth_source,
    )
    return await _issue_login_token_response(db, user=user, request=request)


@router.post("/login/json", response_model=Token, include_in_schema=False)
async def login_json(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Login endpoint accepting JSON body.

    The Vue UI posts JSON (application/json) by default. OAuth2PasswordRequestForm
    expects application/x-www-form-urlencoded and would normally trigger a CORS
    preflight.

    This endpoint keeps the same token response shape.
    """
    if payload.get("code") and payload.get("target") and payload.get("type"):
        if (payload.get("auth_source") or "external").strip().lower() == "internal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Internal employee login does not support verification-code mode",
            )
        target = payload.get("target")
        code_type = payload.get("type")
        code = payload.get("code")
        # Generic failure used for "wrong code", "no such user", and "user
        # cannot use code login". Returning the same response for all of these
        # avoids leaking whether a phone/email is registered or active.
        invalid_credentials = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )
        ok = await VerificationService.verify_code(db, target, code_type, "login", code)
        if not ok:
            raise invalid_credentials
        service = UserService(db)
        if code_type == "email":
            user = await service.get_user_by_email(target)
        else:
            user = await service.get_user_by_phone(target)
        if not user:
            raise invalid_credentials
        if (getattr(user, "auth_source", "local") or "local") == "security_server":
            # Internal accounts must not be reachable via the external code
            # login path. Use the generic error to avoid leaking the routing.
            raise invalid_credentials
        if not getattr(user, "is_active", False):
            # Pending-approval / disabled accounts cannot acquire a token via
            # code login — reject before the privileged token issuance path.
            raise invalid_credentials
    else:
        username = payload.get("username")
        password = payload.get("password")
        # Default to external login for JSON clients to avoid accidental fallback
        # to internal security-server auth when auth_source is omitted.
        auth_source = payload.get("auth_source") or "external"
        if not username or not password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing username or password")
        user = await _resolve_password_login_user(
            db,
            username=username,
            password=password,
            auth_source=auth_source,
        )

    return await _issue_login_token_response(db, user=user, request=request)


@router.post("/verification-code", response_model=VerificationCodeResponse)
async def send_verification_code(
    payload: VerificationCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """发送验证码。生产默认不在响应中回显验证码。"""
    try:
        record = await VerificationService.create_code(
            db,
            target=payload.target,
            code_type=payload.type,
            purpose=payload.purpose,
        )
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return VerificationCodeResponse(
        target=record.target,
        type=record.type,
        purpose=record.purpose,
        code=record.code if settings.VERIFICATION_CODE_RETURN_IN_RESPONSE else None,
        expires_at=record.expires_at,
    )


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/logout")
async def logout():
    """退出登录"""
    return {"message": "Logged out successfully"}
