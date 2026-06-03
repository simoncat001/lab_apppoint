from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.core.audit import diff_payload, record_audit
from app.db.session import get_db
from app.models.user import User
from app.schemas.staff_charge import (
    StaffChargeCreate,
    StaffChargeDetail,
    StaffChargeEnd,
    StaffChargeResponse,
    StaffChargeStats,
    StaffChargeUpdate,
)
from app.services.staff_charge_service import StaffChargeService

router = APIRouter()


def _staff_only(user: User) -> None:
    if not (user.is_staff or user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage staff charges",
        )


def _ensure_charge_in_current_project(charge, project_ctx: CurrentProjectContext) -> None:
    if int(getattr(charge, "project_id", 0) or 0) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found",
        )


async def _get_charge_in_current_project(
    db: AsyncSession,
    charge_id: int,
    project_ctx: CurrentProjectContext,
):
    charge = await StaffChargeService.get_staff_charge(db, charge_id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found",
        )
    _ensure_charge_in_current_project(charge, project_ctx)
    return charge


async def _ensure_staff_member_exists(db: AsyncSession, staff_member_id: int) -> User:
    staff_member = await db.get(User, staff_member_id)
    if not staff_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
    if not (staff_member.is_staff or staff_member.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="staff_member_id must refer to a staff user",
        )
    return staff_member


@router.get("/", response_model=List[StaffChargeResponse])
async def get_staff_charges(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    staff_member_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    in_progress_only: bool = Query(False),
    validated_only: bool = Query(False),
    billable_only: bool = Query(False),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取员工收费记录列表"""
    if project_id is not None and int(project_id) != int(project_ctx.project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project_id must match current project")
    project_id = project_ctx.project_id
    if not (current_user.is_staff or current_user.is_superuser):
        customer_id = current_user.id

    items = await StaffChargeService.get_staff_charges(
        db, skip, limit, staff_member_id, customer_id, project_id,
        in_progress_only, validated_only, billable_only, start_date, end_date
    )
    total = await StaffChargeService.count_staff_charges(
        db, staff_member_id, customer_id, project_id,
        in_progress_only, validated_only, billable_only, start_date, end_date,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.post("/", response_model=StaffChargeResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_charge(
    charge: StaffChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建员工收费记录（开始服务）
    
    - 员工可以为客户创建服务记录
    - 记录开始时间和相关信息
    """
    _staff_only(current_user)
    await _ensure_staff_member_exists(db, charge.staff_member_id)
    charge.project_id = project_ctx.project_id
    
    return await StaffChargeService.create_staff_charge(db, charge)


@router.get("/stats", response_model=StaffChargeStats)
async def get_staff_charge_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    staff_member_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取员工收费统计（需要管理员权限）"""
    _staff_only(current_user)
    if project_id is not None and int(project_id) != int(project_ctx.project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project_id must match current project")
    project_id = project_ctx.project_id
    
    return await StaffChargeService.get_staff_charge_stats(
        db, start_date, end_date, staff_member_id, customer_id, project_id
    )


@router.get("/{charge_id}", response_model=StaffChargeDetail)
async def get_staff_charge(
    charge_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取员工收费记录详情"""
    charge = await _get_charge_in_current_project(db, charge_id, project_ctx)
    if (
        not (current_user.is_staff or current_user.is_superuser)
        and int(charge.customer_id) != int(current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this staff charge",
        )
    
    # 添加计算属性
    response = StaffChargeDetail.model_validate(charge)
    response.duration_minutes = charge.duration_minutes()
    response.is_in_progress = charge.is_in_progress
    response.is_billable = charge.is_billable
    
    return response


@router.post("/{charge_id}/end", response_model=StaffChargeResponse)
async def end_staff_charge(
    charge_id: int,
    end_data: StaffChargeEnd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """结束员工收费记录"""
    _staff_only(current_user)
    charge = await _get_charge_in_current_project(db, charge_id, project_ctx)
    
    # 只有服务员工或管理员可以结束
    if charge.staff_member_id != current_user.id and not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the staff member or administrator can end this charge"
        )
    
    try:
        return await StaffChargeService.end_staff_charge(db, charge_id, end_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{charge_id}", response_model=StaffChargeResponse)
async def update_staff_charge(
    charge_id: int,
    charge: StaffChargeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新员工收费记录（需要管理员权限）"""
    _staff_only(current_user)
    existing = await _get_charge_in_current_project(db, charge_id, project_ctx)
    before_snapshot = {
        "end_time": getattr(existing, "end_time", None),
        "amount": getattr(existing, "amount", None),
        "validated": getattr(existing, "validated", None),
        "waived": getattr(existing, "waived", None),
        "note": getattr(existing, "note", None),
    }

    updated = await StaffChargeService.update_staff_charge(db, charge_id, charge)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found"
        )
    after_snapshot = {
        "end_time": getattr(updated, "end_time", None),
        "amount": getattr(updated, "amount", None),
        "validated": getattr(updated, "validated", None),
        "waived": getattr(updated, "waived", None),
        "note": getattr(updated, "note", None),
    }
    await record_audit(
        db,
        user_id=current_user.id,
        action="STAFF_CHARGE_UPDATE",
        detail={
            "charge_id": int(charge_id),
            "project_id": project_ctx.project_id,
            "changes": diff_payload(before_snapshot, after_snapshot),
        },
    )
    return updated


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff_charge(
    charge_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除员工收费记录（需要管理员权限）"""
    _staff_only(current_user)
    existing = await _get_charge_in_current_project(db, charge_id, project_ctx)
    snapshot = {
        "staff_member_id": getattr(existing, "staff_member_id", None),
        "customer_id": getattr(existing, "customer_id", None),
        "amount": getattr(existing, "amount", None),
        "validated": getattr(existing, "validated", None),
        "waived": getattr(existing, "waived", None),
    }

    deleted = await StaffChargeService.delete_staff_charge(db, charge_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="STAFF_CHARGE_DELETE",
        detail={
            "charge_id": int(charge_id),
            "project_id": project_ctx.project_id,
            "snapshot": snapshot,
        },
    )


@router.get("/staff/{staff_member_id}/active", response_model=List[StaffChargeResponse])
async def get_active_charges_for_staff(
    staff_member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取员工当前的所有服务记录"""
    _staff_only(current_user)
    # 只能查看自己的或管理员可以查看所有
    if staff_member_id != current_user.id and not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own active charges"
        )
    
    charges = await StaffChargeService.get_active_charges_for_staff(db, staff_member_id)
    return [charge for charge in charges if int(charge.project_id) == int(project_ctx.project_id)]


@router.get("/customer/{customer_id}/active", response_model=List[StaffChargeResponse])
async def get_active_charges_for_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取客户当前接受的所有服务记录"""
    # 只能查看自己的或管理员可以查看所有
    if customer_id != current_user.id and not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own charges"
        )
    
    charges = await StaffChargeService.get_active_charges_for_customer(db, customer_id)
    return [charge for charge in charges if int(charge.project_id) == int(project_ctx.project_id)]


@router.post("/{charge_id}/validate", response_model=StaffChargeResponse)
async def validate_staff_charge(
    charge_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """验证员工收费记录（需要管理员权限）"""
    _staff_only(current_user)
    await _get_charge_in_current_project(db, charge_id, project_ctx)

    charge = await StaffChargeService.validate_staff_charge(db, charge_id, current_user.id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="STAFF_CHARGE_VALIDATE",
        detail={
            "charge_id": int(charge_id),
            "project_id": project_ctx.project_id,
            "amount": getattr(charge, "amount", None),
            "customer_id": getattr(charge, "customer_id", None),
        },
    )
    return charge


@router.post("/{charge_id}/waive", response_model=StaffChargeResponse)
async def waive_staff_charge(
    charge_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """豁免员工收费记录（不计费，需要管理员权限）"""
    _staff_only(current_user)
    existing = await _get_charge_in_current_project(db, charge_id, project_ctx)
    pre_amount = getattr(existing, "amount", None)

    charge = await StaffChargeService.waive_staff_charge(db, charge_id, current_user.id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff charge not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="STAFF_CHARGE_WAIVE",
        detail={
            "charge_id": int(charge_id),
            "project_id": project_ctx.project_id,
            "amount_before_waive": pre_amount,
            "customer_id": getattr(charge, "customer_id", None),
        },
    )
    return charge
