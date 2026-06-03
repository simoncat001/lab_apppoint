from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.api.project_context import (
    CurrentProjectContext,
    get_bill_in_current_project,
    get_current_project_context,
)
from app.core.audit import diff_payload, record_audit
from app.db.session import get_db
from app.models.user import User
from app.models.usage_event import UsageEvent
from app.models.project import Project
from app.schemas.bill import BillResponse, BillDetailResponse, BillGenerationRequest, BillUpdate
from app.schemas.user import UserBasic
from app.schemas.usage_event import UsageEventResponse
from app.services.account_service import AccountService
from app.services.billing_service import BillingService
from app.services.usage_event_service import UsageEventService

router = APIRouter()



@router.post("/generate", response_model=List[BillResponse])
async def generate_bills(
    request: BillGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    手动触发账单生成 (需要管理员权限)

    当前规则（无周期）：
    - 合并历史所有未结算账单（按用户）
    - 把未出账但已验证的使用记录金额加进来
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以生成账单"
        )
    
    if project_ctx.project.account_id is None:
        raise HTTPException(status_code=400, detail="当前项目未绑定收款账户")
    scoped_account_id = int(project_ctx.project.account_id)
    if request.account_ids and scoped_account_id not in [int(a) for a in request.account_ids]:
        raise HTTPException(status_code=403, detail="请求的账户范围不包含当前项目收款账户")
    bills = await BillingService.generate_bills(db, [scoped_account_id])
    await record_audit(
        db,
        user_id=current_user.id,
        action="BILL_GENERATE",
        detail={
            "project_id": project_ctx.project_id,
            "account_id": scoped_account_id,
            "bill_ids": [int(b.id) for b in bills],
            "count": len(bills),
        },
    )
    return bills

@router.get("/", response_model=List[BillResponse])
async def get_bills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    account_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取账单列表"""
    # 普通用户：查看自己可访问的付款账户账单，不再强制绑定当前项目收款账户
    if not (current_user.is_staff or current_user.is_superuser):
        accounts = await AccountService.get_accounts_for_user(
            db,
            current_user.id,
            skip=0,
            limit=1000,
            active=True,
        )
        allowed_account_ids = [a.id for a in accounts]
        if not allowed_account_ids:
            return []

        if account_id is not None and account_id not in allowed_account_ids:
            # Do not hard-fail list page for users who cannot access the
            # current project's billing account. Return empty list instead.
            return []

        if account_id is not None:
            return await BillingService.get_bills(db, skip, limit, account_id=account_id)
        return await BillingService.get_bills(db, skip, limit, account_ids=allowed_account_ids)

    if project_ctx.project.account_id is None:
        return []
    scoped_account_id = int(project_ctx.project.account_id)
    if account_id is not None and int(account_id) != scoped_account_id:
        raise HTTPException(status_code=403, detail="只能查看当前项目的账单")
    account_id = scoped_account_id

    return await BillingService.get_bills(db, skip, limit, account_id=account_id)


@router.get("/{bill_id}", response_model=BillDetailResponse)
async def get_bill_detail(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取账单详情（包含关联使用记录和用户信息）"""
    bill = await BillingService.get_bill_detail(db, bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账单不存在",
        )

    if current_user.is_staff or current_user.is_superuser:
        if project_ctx.project.account_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前项目未绑定收款账户")
        if int(bill.account_id) != int(project_ctx.project.account_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账单不属于当前项目")
    else:
        # 普通用户可看本人账户或其组织账户的账单（与当前项目收款账户解耦）
        account = bill.account
        if account is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该账单")
        is_member = await AccountService.user_is_account_member(db, account.id, current_user.id)
        if account.user_id != current_user.id and not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该账单")

    # 确保关联完整：把该账号下符合出账条件但尚未出账的使用记录挂到该账单（仅未结算账单）
    if bill.status in {"DRAFT", "ISSUED"}:
        await BillingService.attach_unbilled_usage_events_to_bill(db, bill)

    user_basic = None
    if bill.account is not None and bill.account.user is not None:
        user_basic = UserBasic.model_validate(bill.account.user)

    # 关联使用记录：只返回真正挂在该账单上的记录（bill_id == 当前账单）
    usage_events = (
        await db.execute(
            select(UsageEvent)
            .options(
                selectinload(UsageEvent.tool),
                selectinload(UsageEvent.project),
                selectinload(UsageEvent.user),
                selectinload(UsageEvent.operator),
            )
            .where(UsageEvent.bill_id == bill.id)
        )
    ).scalars().all()

    usage_events = sorted(list(usage_events), key=lambda e: (e.start or datetime.min))
    usage_events = await UsageEventService.refresh_event_amounts_for_display(db, usage_events)

    return BillDetailResponse(
        **BillResponse.model_validate(bill).model_dump(),
        user=user_basic,
        usage_events=[UsageEventResponse.model_validate(e) for e in usage_events],
    )


@router.put("/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: int,
    bill_in: BillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """编辑账单（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以编辑账单",
        )

    existing = await get_bill_in_current_project(db, bill_id, project_ctx)
    before_snapshot = {
        "status": getattr(existing, "status", None),
        "due_date": getattr(existing, "due_date", None),
        "total_amount": getattr(existing, "total_amount", None),
    }

    if bill_in.status is not None:
        allowed = {"DRAFT", "ISSUED", "PAID", "CANCELLED"}
        if bill_in.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"账单状态无效，可选值：{sorted(allowed)}",
            )

    updated = await BillingService.update_bill(db, bill_id, bill_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账单不存在",
        )

    after_snapshot = {
        "status": getattr(updated, "status", None),
        "due_date": getattr(updated, "due_date", None),
        "total_amount": getattr(updated, "total_amount", None),
    }
    await record_audit(
        db,
        user_id=current_user.id,
        action="BILL_UPDATE",
        detail={
            "bill_id": int(bill_id),
            "project_id": project_ctx.project_id,
            "changes": diff_payload(before_snapshot, after_snapshot),
        },
    )
    return updated
