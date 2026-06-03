from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import (
    AccountBasic,
    AccountCreate,
    AccountDetail,
    AccountMembershipChangeRequestCreate,
    AccountMembershipChangeRequestResponse,
    AccountMembershipChangeRequestReview,
    AccountMembershipChangeRequestStatus,
    AccountTypeCreate,
    AccountTypeResponse,
    AccountTypeUpdate,
    AccountUpdate,
    AccountMemberUpdate,
)
from app.schemas.user import UserBasic
from app.services.account_service import (
    AccountMembershipChangeRequestError,
    AccountProjectBindingError,
    AccountService,
)

router = APIRouter()


def _ensure_account_admin(current_user: User) -> None:
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以执行此操作",
        )


def _ensure_external_membership_applicant(current_user: User) -> None:
    auth_source = (getattr(current_user, "auth_source", None) or "local").lower()
    is_external_user = auth_source == "local" and not bool(
        getattr(current_user, "is_superuser", False)
    )
    if not is_external_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有外部用户可以使用所属账户申请功能",
        )


# AccountType endpoints
@router.get("/account-types", response_model=List[AccountTypeResponse])
async def get_account_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账户类型列表"""
    return await AccountService.get_account_types(db, skip, limit)


@router.post("/account-types", response_model=AccountTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_account_type(
    account_type: AccountTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建账户类型（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建账户类型"
        )
    return await AccountService.create_account_type(db, account_type)


@router.get("/account-types/{type_id}", response_model=AccountTypeResponse)
async def get_account_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账户类型详情"""
    account_type = await AccountService.get_account_type(db, type_id)
    if not account_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户类型不存在"
        )
    return account_type


@router.put("/account-types/{type_id}", response_model=AccountTypeResponse)
async def update_account_type(
    type_id: int,
    account_type: AccountTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新账户类型（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新账户类型"
        )
    
    updated = await AccountService.update_account_type(db, type_id, account_type)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户类型不存在"
        )
    return updated


@router.delete("/account-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除账户类型（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除账户类型"
        )
    
    deleted = await AccountService.delete_account_type(db, type_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户类型不存在"
        )


# Account endpoints
@router.get("/", response_model=List[AccountDetail])
async def get_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active: bool | None = Query(None),
    type_id: int | None = Query(None),
    user_id: int | None = Query(None),
    reservable_project_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账户列表"""
    effective_user_id = user_id
    if not current_user.is_staff and not current_user.is_superuser:
        effective_user_id = current_user.id
    elif effective_user_id is None and reservable_project_id is not None:
        effective_user_id = current_user.id

    if reservable_project_id is not None and effective_user_id is not None:
        return await AccountService.get_reservable_accounts_for_user(
            db,
            effective_user_id,
            reservable_project_id,
            skip=skip,
            limit=limit,
            active=active,
            type_id=type_id,
        )

    if effective_user_id is not None and (not current_user.is_staff and not current_user.is_superuser or user_id is not None):
        return await AccountService.get_accounts_for_user(
            db,
            effective_user_id,
            skip=skip,
            limit=limit,
            active=active,
            type_id=type_id,
        )

    return await AccountService.get_accounts(db, skip, limit, active=active, type_id=type_id)


@router.post("/", response_model=AccountDetail, status_code=status.HTTP_201_CREATED)
async def create_account(
    account: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建账户（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建账户"
        )

    if account.user_id is not None:
        account = account.model_copy(update={"user_id": None})

    # 检查名称是否已存在
    existing = await AccountService.get_account_by_name(db, account.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账户名称已存在"
        )
    try:
        return await AccountService.create_account(db, account)
    except AccountProjectBindingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.get("/joinable-organizations", response_model=List[AccountBasic])
async def get_joinable_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取可申请加入的组织账户列表（仅手动成员管理类型）"""
    _ensure_external_membership_applicant(current_user)
    return await AccountService.get_joinable_organization_accounts(db)


@router.get(
    "/membership-change-requests/my",
    response_model=List[AccountMembershipChangeRequestResponse],
)
async def get_my_membership_change_requests(
    status_filter: AccountMembershipChangeRequestStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的所属账户加入申请"""
    _ensure_external_membership_applicant(current_user)
    return await AccountService.list_membership_change_requests_for_user(
        db,
        current_user.id,
        status=status_filter,
        limit=limit,
    )


@router.post(
    "/membership-change-requests",
    response_model=AccountMembershipChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_membership_change_request(
    payload: AccountMembershipChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交所属账户加入申请"""
    _ensure_external_membership_applicant(current_user)
    try:
        return await AccountService.create_membership_change_request(
            db,
            requester_user=current_user,
            target_account_id=payload.target_account_id,
            reason=payload.reason,
        )
    except AccountMembershipChangeRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.post(
    "/membership-change-requests/{request_id}/cancel",
    response_model=AccountMembershipChangeRequestResponse,
)
async def cancel_membership_change_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销本人待审批的所属账户加入申请"""
    _ensure_external_membership_applicant(current_user)
    try:
        request_obj = await AccountService.cancel_membership_change_request(
            db,
            request_id=request_id,
            requester_user=current_user,
        )
    except AccountMembershipChangeRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="所属账户加入申请不存在",
        )
    return request_obj


@router.get(
    "/membership-change-requests",
    response_model=List[AccountMembershipChangeRequestResponse],
)
async def get_membership_change_requests(
    status_filter: AccountMembershipChangeRequestStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所属账户加入申请列表（管理员）"""
    _ensure_account_admin(current_user)
    return await AccountService.list_membership_change_requests(
        db,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/membership-change-requests/{request_id}/approve",
    response_model=AccountMembershipChangeRequestResponse,
)
async def approve_membership_change_request(
    request_id: int,
    payload: AccountMembershipChangeRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批通过所属账户加入申请（管理员）"""
    _ensure_account_admin(current_user)
    try:
        request_obj = await AccountService.approve_membership_change_request(
            db,
            request_id=request_id,
            reviewer_user=current_user,
            comment=payload.comment,
        )
    except AccountMembershipChangeRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="所属账户加入申请不存在",
        )
    return request_obj


@router.post(
    "/membership-change-requests/{request_id}/reject",
    response_model=AccountMembershipChangeRequestResponse,
)
async def reject_membership_change_request(
    request_id: int,
    payload: AccountMembershipChangeRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """驳回所属账户加入申请（管理员）"""
    _ensure_account_admin(current_user)
    try:
        request_obj = await AccountService.reject_membership_change_request(
            db,
            request_id=request_id,
            reviewer_user=current_user,
            comment=payload.comment,
        )
    except AccountMembershipChangeRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="所属账户加入申请不存在",
        )
    return request_obj


@router.get("/{account_id}", response_model=AccountDetail)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账户详情"""
    account = await AccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    if not current_user.is_staff and not current_user.is_superuser:
        is_member = await AccountService.user_is_account_member(db, account_id, current_user.id)
        if account.user_id != current_user.id and not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问该账户"
            )
    return account


@router.get("/{account_id}/members", response_model=List[UserBasic])
async def get_account_members(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账户成员列表"""
    account = await AccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    if not current_user.is_staff and not current_user.is_superuser:
        is_member = await AccountService.user_is_account_member(db, account_id, current_user.id)
        if account.user_id != current_user.id and not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问该账户"
            )
    return [UserBasic.model_validate(user) for user in account.members]


@router.put("/{account_id}/members", response_model=AccountDetail)
async def set_account_members(
    account_id: int,
    payload: AccountMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新账户成员（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新账户成员"
        )
    try:
        updated = await AccountService.set_account_members(db, account_id, payload.user_ids)
    except AccountProjectBindingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    return updated


@router.put("/{account_id}", response_model=AccountDetail)
async def update_account(
    account_id: int,
    account: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新账户（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新账户"
        )

    if account.user_id is not None:
        account = account.model_copy(update={"user_id": None})

    try:
        updated = await AccountService.update_account(db, account_id, account)
    except AccountProjectBindingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    return updated


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除账户（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除账户"
        )
    
    try:
        deleted = await AccountService.delete_account(db, account_id)
    except AccountProjectBindingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )


@router.post("/{account_id}/activate", response_model=AccountDetail)
async def activate_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """激活账户（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以激活账户"
        )
    
    account = await AccountService.activate_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    return account


@router.post("/{account_id}/deactivate", response_model=AccountDetail)
async def deactivate_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """停用账户（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以停用账户"
        )
    
    try:
        account = await AccountService.deactivate_account(db, account_id)
    except AccountProjectBindingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )
    return account
