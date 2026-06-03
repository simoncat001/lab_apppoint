from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.staff_charge import StaffCharge
from app.models.project import Project
from app.schemas.staff_charge import StaffChargeCreate, StaffChargeEnd, StaffChargeUpdate
from app.services.account_service import AccountService


class StaffChargeService:
    """员工收费服务"""

    @staticmethod
    async def get_staff_charges(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        staff_member_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        project_id: Optional[int] = None,
        in_progress_only: bool = False,
        validated_only: bool = False,
        billable_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StaffCharge]:
        """获取员工收费记录列表"""
        query = select(StaffCharge).options(
            selectinload(StaffCharge.staff_member),
            selectinload(StaffCharge.customer),
            selectinload(StaffCharge.project),
            selectinload(StaffCharge.validated_by),
            selectinload(StaffCharge.waived_by)
        )
        
        # 应用过滤条件
        filters = []
        if staff_member_id:
            filters.append(StaffCharge.staff_member_id == staff_member_id)
        if customer_id:
            filters.append(StaffCharge.customer_id == customer_id)
        if project_id:
            filters.append(StaffCharge.project_id == project_id)
        if in_progress_only:
            filters.append(StaffCharge.end == None)
        if validated_only:
            filters.append(StaffCharge.validated == True)
        if billable_only:
            filters.append(StaffCharge.waived == False)
        if start_date:
            filters.append(StaffCharge.start >= start_date)
        if end_date:
            filters.append(StaffCharge.start <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(StaffCharge.start.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_staff_charges(
        db: AsyncSession,
        staff_member_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        project_id: Optional[int] = None,
        in_progress_only: bool = False,
        validated_only: bool = False,
        billable_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        query = select(func.count(StaffCharge.id))
        filters = []
        if staff_member_id:
            filters.append(StaffCharge.staff_member_id == staff_member_id)
        if customer_id:
            filters.append(StaffCharge.customer_id == customer_id)
        if project_id:
            filters.append(StaffCharge.project_id == project_id)
        if in_progress_only:
            filters.append(StaffCharge.end == None)
        if validated_only:
            filters.append(StaffCharge.validated == True)
        if billable_only:
            filters.append(StaffCharge.waived == False)
        if start_date:
            filters.append(StaffCharge.start >= start_date)
        if end_date:
            filters.append(StaffCharge.start <= end_date)
        if filters:
            query = query.where(and_(*filters))
        result = await db.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def get_staff_charge(db: AsyncSession, charge_id: int) -> Optional[StaffCharge]:
        """获取单个员工收费记录"""
        result = await db.execute(
            select(StaffCharge)
            .options(
                selectinload(StaffCharge.staff_member),
                selectinload(StaffCharge.customer),
                selectinload(StaffCharge.project),
                selectinload(StaffCharge.validated_by),
                selectinload(StaffCharge.waived_by)
            )
            .where(StaffCharge.id == charge_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_staff_charge(
        db: AsyncSession,
        charge_data: StaffChargeCreate
    ) -> StaffCharge:
        """创建员工收费记录（开始服务）"""
        charge_dict = charge_data.model_dump()
        
        # 设置开始时间
        if not charge_dict.get("start"):
            charge_dict["start"] = datetime.utcnow()
        
        charge = StaffCharge(**charge_dict)
        db.add(charge)
        await db.commit()
        await db.refresh(charge)
        return charge

    @staticmethod
    async def end_staff_charge(
        db: AsyncSession,
        charge_id: int,
        end_data: StaffChargeEnd
    ) -> Optional[StaffCharge]:
        """结束员工收费记录"""
        result = await db.execute(
            select(StaffCharge).where(StaffCharge.id == charge_id)
        )
        charge = result.scalar_one_or_none()
        
        if not charge:
            return None
        
        if charge.end is not None:
            raise ValueError("Staff charge has already ended")
        
        charge.end = datetime.utcnow()
        if end_data.note:
            charge.note = end_data.note
        
        await db.commit()
        await db.refresh(charge)
        return charge

    @staticmethod
    async def update_staff_charge(
        db: AsyncSession,
        charge_id: int,
        charge_data: StaffChargeUpdate
    ) -> Optional[StaffCharge]:
        """更新员工收费记录"""
        result = await db.execute(
            select(StaffCharge).where(StaffCharge.id == charge_id)
        )
        charge = result.scalar_one_or_none()
        
        if not charge:
            return None

        was_validated = bool(charge.validated)
        
        update_data = charge_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(charge, field, value)

        # Keep balance/credit consistent if staff toggles validated via the generic update endpoint.
        is_validated = bool(getattr(charge, "validated", False))
        if not was_validated and is_validated:
            if not charge.waived and charge.amount:
                account_id = await db.scalar(
                    select(Project.account_id).where(Project.id == charge.project_id)
                )
                if account_id is not None:
                    await AccountService.consume_balance_or_credit(
                        db, account_id, Decimal(str(charge.amount or 0))
                    )
        elif was_validated and not is_validated:
            if not charge.waived and charge.amount:
                account_id = await db.scalar(
                    select(Project.account_id).where(Project.id == charge.project_id)
                )
                if account_id is not None:
                    await AccountService.refund_balance_or_credit(
                        db, account_id, Decimal(str(charge.amount or 0))
                    )
        
        await db.commit()
        await db.refresh(charge)
        return charge

    @staticmethod
    async def delete_staff_charge(db: AsyncSession, charge_id: int) -> bool:
        """删除员工收费记录"""
        result = await db.execute(
            select(StaffCharge).where(StaffCharge.id == charge_id)
        )
        charge = result.scalar_one_or_none()
        
        if not charge:
            return False
        
        await db.delete(charge)
        await db.commit()
        return True

    @staticmethod
    async def get_active_charges_for_staff(
        db: AsyncSession,
        staff_member_id: int
    ) -> List[StaffCharge]:
        """获取员工当前的所有服务记录"""
        result = await db.execute(
            select(StaffCharge)
            .options(
                selectinload(StaffCharge.customer),
                selectinload(StaffCharge.project)
            )
            .where(
                and_(
                    StaffCharge.staff_member_id == staff_member_id,
                    StaffCharge.end == None
                )
            )
            .order_by(StaffCharge.start.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_active_charges_for_customer(
        db: AsyncSession,
        customer_id: int
    ) -> List[StaffCharge]:
        """获取客户当前接受的所有服务记录"""
        result = await db.execute(
            select(StaffCharge)
            .options(
                selectinload(StaffCharge.staff_member),
                selectinload(StaffCharge.project)
            )
            .where(
                and_(
                    StaffCharge.customer_id == customer_id,
                    StaffCharge.end == None
                )
            )
            .order_by(StaffCharge.start.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def validate_staff_charge(
        db: AsyncSession,
        charge_id: int,
        validator_id: int
    ) -> Optional[StaffCharge]:
        """验证员工收费记录"""
        result = await db.execute(
            select(StaffCharge).where(StaffCharge.id == charge_id)
        )
        charge = result.scalar_one_or_none()
        
        if not charge:
            return None

        # Idempotency: don't double-charge.
        if charge.validated:
            return charge
        
        charge.validated = True
        charge.validated_by_id = validator_id

        # Deduct from account funds when the charge becomes billable.
        if not charge.waived and charge.amount:
            account_id = await db.scalar(
                select(Project.account_id).where(Project.id == charge.project_id)
            )
            if account_id is not None:
                await AccountService.consume_balance_or_credit(
                    db, account_id, Decimal(str(charge.amount or 0))
                )
        
        await db.commit()
        await db.refresh(charge)
        return charge

    @staticmethod
    async def waive_staff_charge(
        db: AsyncSession,
        charge_id: int,
        waiver_id: int
    ) -> Optional[StaffCharge]:
        """豁免员工收费记录（不计费）"""
        result = await db.execute(
            select(StaffCharge).where(StaffCharge.id == charge_id)
        )
        charge = result.scalar_one_or_none()
        
        if not charge:
            return None

        if charge.waived:
            return charge

        # Refund previously consumed account funds (best-effort).
        if charge.validated and charge.amount:
            account_id = await db.scalar(
                select(Project.account_id).where(Project.id == charge.project_id)
            )
            if account_id is not None:
                await AccountService.refund_balance_or_credit(
                    db, account_id, Decimal(str(charge.amount or 0))
                )
        
        charge.waived = True
        charge.waived_on = datetime.utcnow()
        charge.waived_by_id = waiver_id
        
        await db.commit()
        await db.refresh(charge)
        return charge

    @staticmethod
    async def get_staff_charge_stats(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        staff_member_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> dict:
        """获取员工收费统计"""
        filters = []
        if start_date:
            filters.append(StaffCharge.start >= start_date)
        if end_date:
            filters.append(StaffCharge.start <= end_date)
        if staff_member_id:
            filters.append(StaffCharge.staff_member_id == staff_member_id)
        if customer_id:
            filters.append(StaffCharge.customer_id == customer_id)
        if project_id:
            filters.append(StaffCharge.project_id == project_id)
        
        # 只统计已结束的记录
        filters.append(StaffCharge.end != None)
        
        query = select(StaffCharge)
        if filters:
            query = query.where(and_(*filters))
        
        result = await db.execute(query)
        charges = result.scalars().all()
        
        total_count = len(charges)
        total_minutes = sum(c.duration_minutes() or 0 for c in charges)
        avg_minutes = total_minutes / total_count if total_count > 0 else 0
        
        # 按员工统计
        by_staff = {}
        for charge in charges:
            by_staff[charge.staff_member_id] = by_staff.get(charge.staff_member_id, 0) + 1
        
        # 按客户统计
        by_customer = {}
        for charge in charges:
            by_customer[charge.customer_id] = by_customer.get(charge.customer_id, 0) + 1
        
        # 按项目统计
        by_project = {}
        for charge in charges:
            by_project[charge.project_id] = by_project.get(charge.project_id, 0) + 1
        
        # 计费统计
        total_billable = sum(1 for c in charges if not c.waived)
        total_waived = sum(1 for c in charges if c.waived)
        
        return {
            "total_count": total_count,
            "total_duration_minutes": total_minutes,
            "average_duration_minutes": avg_minutes,
            "by_staff": by_staff,
            "by_customer": by_customer,
            "by_project": by_project,
            "total_billable": total_billable,
            "total_waived": total_waived
        }
