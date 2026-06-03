"""
Reservation service layer
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.reservation import Reservation
from app.models.tool import Tool
from app.schemas.reservation import ReservationCreate, ReservationUpdate


class ReservationAvailabilityError(ValueError):
    """Raised when a reservation slot is no longer available inside the write lock."""


class ReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _reservation_query_with_relations(self):
        return select(Reservation).options(
            selectinload(Reservation.user),
            selectinload(Reservation.tool),
            selectinload(Reservation.project),
        )
    
    async def get_reservations(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: int = None,
        tool_id: int = None,
        project_id: int = None,
        category_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
        cancelled: Optional[bool] = False,
    ) -> List[Reservation]:
        """获取预约列表。

        ``cancelled``: ``False`` 仅未取消（默认，向后兼容），``True`` 仅已取消，``None`` 全部。
        """
        query = self._reservation_query_with_relations()
        if cancelled is not None:
            query = query.where(Reservation.cancelled == cancelled)

        if user_id:
            query = query.where(Reservation.user_id == user_id)
        if tool_id:
            query = query.where(Reservation.tool_id == tool_id)
        if project_id:
            query = query.where(Reservation.project_id == project_id)
        if category_id:
            query = query.join(Tool, Reservation.tool_id == Tool.id).where(Tool.category_id == category_id)
        if start_date:
            query = query.where(Reservation.end >= start_date)
        if end_date:
            query = query.where(Reservation.start <= end_date)

        query = query.offset(skip).limit(limit).order_by(Reservation.start.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_reservations(
        self,
        user_id: int = None,
        tool_id: int = None,
        project_id: int = None,
        category_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
        cancelled: Optional[bool] = False,
    ) -> int:
        query = select(func.count(func.distinct(Reservation.id))).select_from(Reservation)
        if category_id:
            query = query.join(Tool, Reservation.tool_id == Tool.id)
        if cancelled is not None:
            query = query.where(Reservation.cancelled == cancelled)
        if user_id:
            query = query.where(Reservation.user_id == user_id)
        if tool_id:
            query = query.where(Reservation.tool_id == tool_id)
        if project_id:
            query = query.where(Reservation.project_id == project_id)
        if category_id:
            query = query.where(Tool.category_id == category_id)
        if start_date:
            query = query.where(Reservation.end >= start_date)
        if end_date:
            query = query.where(Reservation.start <= end_date)
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def get_occupied_slots(
        self,
        tool_id: int,
        project_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Reservation]:
        """获取仪器在指定时间范围内的占用时段"""
        query = select(Reservation).where(
            Reservation.tool_id == tool_id,
            Reservation.project_id == project_id,
            Reservation.cancelled == False,
            Reservation.missed == False,
            Reservation.end >= start_date,
            Reservation.start <= end_date,
        ).order_by(Reservation.start.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_reservations_for_day(
        self,
        *,
        tool_id: int,
        day_start: datetime,
        day_end: datetime,
        exclude_id: int | None = None,
        lock_rows: bool = False,
    ) -> int:
        filters = [
            Reservation.tool_id == tool_id,
            Reservation.cancelled == False,
            Reservation.start < day_end,
            Reservation.end > day_start,
        ]
        if exclude_id:
            filters.append(Reservation.id != exclude_id)

        if lock_rows:
            result = await self.db.execute(
                select(Reservation.id)
                .where(*filters)
                .with_for_update()
            )
            return len(result.scalars().all())

        query = select(func.count()).select_from(Reservation).where(*filters)
        result = await self.db.execute(query)
        return int(result.scalar_one() or 0)
    
    async def get_reservation(self, reservation_id: int) -> Optional[Reservation]:
        """获取单个预约"""
        result = await self.db.execute(
            self._reservation_query_with_relations().where(Reservation.id == reservation_id)
        )
        return result.scalars().first()
    
    async def check_reservation_conflict(
        self,
        tool_id: int,
        start: datetime,
        end: datetime,
        exclude_id: int = None,
        lock_rows: bool = False,
    ) -> bool:
        """检查预约冲突"""
        query = select(Reservation.id if lock_rows else Reservation).where(
            and_(
                Reservation.tool_id == tool_id,
                Reservation.cancelled == False,
                or_(
                    and_(Reservation.start < end, Reservation.end > start),
                )
            )
        )
        
        if exclude_id:
            query = query.where(Reservation.id != exclude_id)
        if lock_rows:
            query = query.with_for_update()
        
        result = await self.db.execute(query)
        return result.scalars().first() is not None

    async def _lock_tool_for_reservation(self, tool_id: int) -> Optional[Tool]:
        """Serialize reservation writes for one instrument.

        MySQL cannot express a non-overlapping datetime range as a simple unique
        constraint, so we lock the instrument row and re-check availability before
        insert/update.
        """
        result = await self.db.execute(
            select(Tool)
            .where(Tool.id == tool_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _lock_reservation(self, reservation_id: int) -> Optional[Reservation]:
        result = await self.db.execute(
            select(Reservation)
            .where(Reservation.id == reservation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _day_bounds(value: datetime) -> tuple[datetime, datetime]:
        day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start, day_start + timedelta(days=1)

    async def _ensure_reservation_available(
        self,
        *,
        tool: Tool,
        start: datetime,
        end: datetime,
        exclude_id: int | None = None,
    ) -> None:
        is_count_based_tool = int(getattr(tool, "price_type", 1) or 1) == 0
        if is_count_based_tool:
            daily_quota = int(getattr(tool, "maximum_reservations_per_day", 0) or 0)
            if daily_quota <= 0:
                return

            day_start, day_end = self._day_bounds(start)
            reserved_count = await self.count_reservations_for_day(
                tool_id=tool.id,
                day_start=day_start,
                day_end=day_end,
                exclude_id=exclude_id,
                lock_rows=True,
            )
            if reserved_count >= daily_quota:
                raise ReservationAvailabilityError("当天预约次数已满，无法继续预约")
            return

        has_conflict = await self.check_reservation_conflict(
            tool_id=tool.id,
            start=start,
            end=end,
            exclude_id=exclude_id,
            lock_rows=True,
        )
        if has_conflict:
            raise ReservationAvailabilityError("Time slot is already reserved")
    
    async def create_reservation(self, reservation_in: ReservationCreate, creator_id: int) -> Reservation:
        """创建预约"""
        tool = await self._lock_tool_for_reservation(reservation_in.tool_id)
        if not tool:
            raise ReservationAvailabilityError("Tool not found")
        await self._ensure_reservation_available(
            tool=tool,
            start=reservation_in.start,
            end=reservation_in.end,
        )

        reservation = Reservation(
            user_id=reservation_in.user_id,
            creator_id=creator_id,
            # creation_time=datetime.utcnow(),
            # title="",
            short_notice=False,
            tool_id=reservation_in.tool_id,
            area_id=reservation_in.area_id,
            project_id=reservation_in.project_id,
            payer_account_id=reservation_in.payer_account_id,
            start=reservation_in.start,
            end=reservation_in.end,
            additional_information=reservation_in.additional_information,
        )
        self.db.add(reservation)
        await self.db.commit()
        loaded = await self.get_reservation(reservation.id)
        return loaded or reservation
    
    async def update_reservation(
        self,
        reservation_id: int,
        reservation_in: ReservationUpdate
    ) -> Optional[Reservation]:
        """更新预约"""
        reservation = await self.get_reservation(reservation_id)
        if not reservation:
            return None
        
        update_data = reservation_in.model_dump(exclude_unset=True)

        if not update_data.get("cancelled") and ("start" in update_data or "end" in update_data):
            tool = await self._lock_tool_for_reservation(reservation.tool_id)
            if not tool:
                raise ReservationAvailabilityError("Tool not found")
            reservation = await self._lock_reservation(reservation_id)
            if not reservation:
                return None
            effective_start = update_data.get("start", reservation.start)
            effective_end = update_data.get("end", reservation.end)
            await self._ensure_reservation_available(
                tool=tool,
                start=effective_start,
                end=effective_end,
                exclude_id=reservation_id,
            )
        
        for field, value in update_data.items():
            setattr(reservation, field, value)
        
        await self.db.commit()
        loaded = await self.get_reservation(reservation_id)
        return loaded or reservation
    
    async def cancel_reservation(self, reservation_id: int) -> bool:
        """取消预约"""
        reservation = await self.get_reservation(reservation_id)
        if not reservation:
            return False
        
        reservation.cancelled = True
        reservation.cancellation_time = datetime.utcnow()
        await self.db.commit()
        return True
