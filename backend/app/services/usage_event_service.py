from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bill import Bill
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.tool import Tool
from app.models.usage_event import UsageEvent
from app.models.tool_rate import ToolRate
from app.schemas.usage_event import UsageEventCreate, UsageEventEnd, UsageEventUpdate, UsageEventSyncResult
from app.services.account_service import AccountService


class UsageEventService:
    """使用记录服务"""

    VALID_USAGE_EVENT_STATUSES = {"pending", "charged", "waived", "in_progress"}

    @staticmethod
    async def _lock_tool_for_usage(db: AsyncSession, tool_id: int) -> Optional[Tool]:
        result = await db.execute(
            select(Tool)
            .where(Tool.id == tool_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _to_naive(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    @staticmethod
    async def _resolve_charge_account_id(db: AsyncSession, event: UsageEvent) -> Optional[int]:
        """Resolve the payable account for a usage event.

        Priority:
        1) usage_event.payer_account_id (new decoupled billing model)
        2) project.account_id (legacy fallback)
        """
        payer_account_id = getattr(event, "payer_account_id", None)
        if payer_account_id is not None:
            return int(payer_account_id)

        if event.project_id is None:
            return None
        legacy_account_id = await db.scalar(
            select(Project.account_id).where(Project.id == event.project_id)
        )
        return int(legacy_account_id) if legacy_account_id is not None else None

    @staticmethod
    def _normalize_status_filter(status: Optional[str]) -> Optional[str]:
        if status is None:
            return None
        normalized = str(status).strip().lower()
        if not normalized:
            return None
        if normalized not in UsageEventService.VALID_USAGE_EVENT_STATUSES:
            raise ValueError("不支持的使用记录状态筛选条件")
        return normalized

    @staticmethod
    def _build_status_filters(status: Optional[str]) -> list:
        normalized = UsageEventService._normalize_status_filter(status)
        if normalized is None:
            return []
        if normalized == "pending":
            return [
                UsageEvent.end != None,
                UsageEvent.validated == False,
                UsageEvent.waived == False,
            ]
        if normalized == "charged":
            return [
                UsageEvent.end != None,
                UsageEvent.validated == True,
                UsageEvent.waived == False,
            ]
        if normalized == "waived":
            return [
                UsageEvent.end != None,
                UsageEvent.waived == True,
            ]
        return [UsageEvent.end == None]

    @staticmethod
    async def _recalculate_event_amount(db: AsyncSession, event: UsageEvent) -> float:
        """根据当前 start/end/tool 重新计算使用记录金额。"""
        if not event.end:
            return 0.0

        # Avoid async lazy-loading relationship attributes here; some callers
        # (for example stats aggregation) only query UsageEvent rows.
        tool = event.__dict__.get("tool")
        if tool is None:
            tool = await db.get(Tool, event.tool_id)

        if tool is None:
            return float(event.amount or 0.0)

        if tool.price_type == 0:
            return float(tool.price_per_use or 0.0)

        return await UsageEventService._calculate_cost(
            db,
            event.tool_id,
            event.start,
            event.end,
            float(tool.price_per_hour or 0.0),
        )

    @staticmethod
    async def refresh_event_amount_for_display(
        db: AsyncSession,
        event: Optional[UsageEvent],
    ) -> Optional[UsageEvent]:
        """在响应返回前按当前价格实时刷新展示金额，不依赖前端计算。"""
        if event is None:
            return None
        event.amount = await UsageEventService._recalculate_event_amount(db, event)
        return event

    @staticmethod
    async def refresh_event_amounts_for_display(
        db: AsyncSession,
        events: List[UsageEvent],
    ) -> List[UsageEvent]:
        for event in events:
            event.amount = await UsageEventService._recalculate_event_amount(db, event)
        return events

    @staticmethod
    async def _find_linked_reservation(
        db: AsyncSession,
        event: UsageEvent,
    ) -> Optional[Reservation]:
        if event.user_id is None or event.tool_id is None:
            return None

        event_start = UsageEventService._to_naive(event.start)
        event_end = UsageEventService._to_naive(event.end) or event_start
        if event_start is None or event_end is None:
            return None

        result = await db.execute(
            select(Reservation)
            .where(
                and_(
                    Reservation.user_id == event.user_id,
                    Reservation.tool_id == event.tool_id,
                    Reservation.project_id == event.project_id,
                    Reservation.cancelled == False,
                    Reservation.start <= event_start + timedelta(minutes=5),
                    Reservation.end >= event_end - timedelta(minutes=5),
                )
            )
            .order_by(Reservation.start.desc(), Reservation.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    @staticmethod
    async def sync_payer_account_from_reservation(
        db: AsyncSession,
        event: UsageEvent,
    ) -> UsageEvent:
        reservation = await UsageEventService._find_linked_reservation(db, event)
        if reservation and reservation.payer_account_id is not None:
            event.payer_account_id = int(reservation.payer_account_id)
        return event

    @staticmethod
    async def _apply_amount_delta_side_effects(
        db: AsyncSession,
        event: UsageEvent,
        old_amount: float,
        new_amount: float,
    ) -> None:
        """对已验证/已出账记录的金额变化进行补差。"""
        delta = Decimal(str(new_amount)) - Decimal(str(old_amount))
        if delta == 0:
            return

        if event.bill_id is not None and not event.waived:
            bill = await db.get(Bill, event.bill_id)
            if bill is not None and getattr(bill, "status", None) != "CANCELLED":
                current_total = Decimal(str(bill.total_amount or 0))
                next_total = current_total + delta
                if next_total < 0:
                    next_total = Decimal("0")
                bill.total_amount = next_total

        if event.validated and not event.waived:
            account_id = await UsageEventService._resolve_charge_account_id(db, event)
            if account_id is not None:
                if delta > 0:
                    await AccountService.consume_balance_or_credit(db, account_id, delta)
                elif delta < 0:
                    await AccountService.refund_balance_or_credit(db, account_id, -delta)

    @staticmethod
    async def recalculate_amounts_for_tool(
        db: AsyncSession,
        tool_id: int,
        *,
        tool: Optional[Tool] = None,
    ) -> int:
        """重算某台仪器所有已结束使用记录的费用金额。

        用于仪器价格变更后，把历史使用记录金额同步刷新，并对已确认/已出账记录做差额补扣或退款。
        """
        result = await db.execute(
            select(UsageEvent)
            .options(selectinload(UsageEvent.tool))
            .where(
                and_(
                    UsageEvent.tool_id == tool_id,
                    UsageEvent.end != None,
                )
            )
        )
        events = list(result.scalars().all())
        updated_count = 0

        for event in events:
            if tool is not None:
                event.tool = tool

            old_amount = float(event.amount or 0.0)
            new_amount = await UsageEventService._recalculate_event_amount(db, event)
            event.amount = new_amount

            if abs(new_amount - old_amount) > 1e-9:
                updated_count += 1
                await UsageEventService._apply_amount_delta_side_effects(
                    db,
                    event,
                    old_amount=old_amount,
                    new_amount=new_amount,
                )

        return updated_count

    @staticmethod
    async def sync_from_reservations(
        db: AsyncSession,
        include_missed: bool = False,
        lookback_days: Optional[int] = None,
        user_id: Optional[int] = None,
        tool_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> UsageEventSyncResult:
        """将已结束的预约同步为使用记录。

        Notes:
        - 预约的“已完成”通常表现为 `end < now` 且未取消。
        - 该项目历史上提供了独立脚本 `sync_reservation_usage.py`，但未集成到 API。
        - 这里的去重策略：同一 tool/user 且 start 落在预约窗口附近则认为已存在。
        """
        # NOTE: In this project, reservation timestamps are stored/compared in
        # DB-local time (see MySQL `NOW()` usage). Using UTC here can cause
        # already-ended reservations to be incorrectly treated as "not ended".
        now = datetime.now()

        reservation_filters = [
            Reservation.end < now,
            Reservation.cancelled == False,
        ]
        if user_id is not None:
            reservation_filters.append(Reservation.user_id == user_id)
        if tool_id is not None:
            reservation_filters.append(Reservation.tool_id == tool_id)
        if project_id is not None:
            reservation_filters.append(Reservation.project_id == project_id)
        if not include_missed:
            reservation_filters.append(Reservation.missed == False)
        if lookback_days is not None:
            reservation_filters.append(Reservation.end >= (now - timedelta(days=lookback_days)))

        reservation_query = select(Reservation).where(and_(*reservation_filters))
        res_result = await db.execute(reservation_query)
        reservations = list(res_result.scalars().all())

        scanned = len(reservations)
        created = 0
        skipped_existing = 0
        skipped_missing_tool = 0

        max_has_ended = await db.scalar(select(func.max(UsageEvent.has_ended)))
        next_has_ended = (max_has_ended or 0) + 1

        for res in reservations:
            # tool_id can be NULL in schema; skip those.
            if res.tool_id is None:
                skipped_missing_tool += 1
                continue

            # Check for an existing usage event that overlaps the reservation window.
            usage_exists_query = (
                select(UsageEvent.id)
                .where(
                    and_(
                        UsageEvent.tool_id == res.tool_id,
                        UsageEvent.user_id == res.user_id,
                        UsageEvent.start >= (res.start - timedelta(minutes=5)),
                        UsageEvent.start <= res.end,
                    )
                )
                .limit(1)
            )
            existing_id = await db.scalar(usage_exists_query)
            if existing_id is not None:
                skipped_existing += 1
                continue

            tool = await db.get(Tool, res.tool_id)
            if not tool:
                skipped_missing_tool += 1
                continue

            start = UsageEventService._to_naive(res.start)
            end = UsageEventService._to_naive(res.end)

            usage_event = UsageEvent(
                user_id=res.user_id,
                operator_id=res.user_id,
                tool_id=res.tool_id,
                project_id=res.project_id,
                payer_account_id=res.payer_account_id,
                start=start,
                end=end,
                remote_work=False,
                has_ended=next_has_ended,
            )

            # Calculate cost
            amount = 0.0
            if tool.price_type == 1:  # Hourly
                base_price = float(tool.price_per_hour) if tool.price_per_hour else 0.0
                amount = await UsageEventService._calculate_cost(db, tool.id, start, end, base_price)
            else:  # Per usage
                amount = float(tool.price_per_use) if tool.price_per_use else 0.0
            usage_event.amount = amount

            db.add(usage_event)
            created += 1
            next_has_ended += 1

        await db.commit()

        return UsageEventSyncResult(
            scanned=scanned,
            created=created,
            skipped_existing=skipped_existing,
            skipped_missing_tool=skipped_missing_tool,
        )

    @staticmethod
    async def upsert_from_completed_reservation(
        db: AsyncSession,
        reservation: Reservation,
        *,
        completed_by_id: int,
    ) -> UsageEvent:
        """Create/update a pending usage event from an admin completion report.

        This intentionally does not validate/charge the event. Charging remains
        the explicit usage-event validation step.
        """
        if reservation.tool_id is None:
            raise ValueError("预约未关联仪器，无法生成使用记录")

        tool = await db.get(Tool, reservation.tool_id)
        if tool is None:
            raise ValueError("预约关联的仪器不存在，无法生成使用记录")

        start = UsageEventService._to_naive(reservation.actual_start or reservation.start)
        end = UsageEventService._to_naive(reservation.actual_end or reservation.end)
        if start is None or end is None or end <= start:
            raise ValueError("实际结束时间必须晚于实际开始时间")

        usage_exists_query = (
            select(UsageEvent)
            .where(
                and_(
                    UsageEvent.tool_id == reservation.tool_id,
                    UsageEvent.user_id == reservation.user_id,
                    UsageEvent.project_id == reservation.project_id,
                    UsageEvent.start >= (UsageEventService._to_naive(reservation.start) - timedelta(minutes=5)),
                    UsageEvent.start <= (UsageEventService._to_naive(reservation.end) + timedelta(minutes=5)),
                )
            )
            .order_by(UsageEvent.start.desc(), UsageEvent.id.desc())
            .limit(1)
        )
        event = (await db.execute(usage_exists_query)).scalars().first()

        if event is not None and (event.validated or event.waived or event.bill_id is not None):
            raise ValueError("关联使用记录已确认或已出账，不能通过完成填报修改")

        amount = 0.0
        if tool.price_type == 1:
            base_price = float(tool.price_per_hour) if tool.price_per_hour else 0.0
            amount = await UsageEventService._calculate_cost(db, tool.id, start, end, base_price)
        else:
            amount = float(tool.price_per_use) if tool.price_per_use else 0.0

        note = reservation.completion_note or "预约完成填报同步"
        if event is None:
            max_has_ended = await db.scalar(select(func.max(UsageEvent.has_ended)))
            event = UsageEvent(
                user_id=reservation.user_id,
                operator_id=reservation.user_id,
                tool_id=reservation.tool_id,
                project_id=reservation.project_id,
                payer_account_id=reservation.payer_account_id,
                start=start,
                end=end,
                amount=amount,
                has_ended=(max_has_ended or 0) + 1,
                validated=False,
                remote_work=False,
                note=note,
                validated_by_id=None,
            )
            db.add(event)
            return event

        event.start = start
        event.end = end
        event.amount = amount
        event.payer_account_id = reservation.payer_account_id
        event.operator_id = reservation.user_id
        event.note = note
        event.validated_by_id = None
        return event

    @staticmethod
    async def get_usage_events(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        tool_id: Optional[int] = None,
        category_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        in_progress_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UsageEvent]:
        """获取使用记录列表"""
        query = select(UsageEvent).options(
            selectinload(UsageEvent.user),
            selectinload(UsageEvent.operator),
            selectinload(UsageEvent.tool),
            selectinload(UsageEvent.project)
        )
        
        # 应用过滤条件
        filters = []
        if user_id:
            filters.append(UsageEvent.user_id == user_id)
        if tool_id:
            filters.append(UsageEvent.tool_id == tool_id)
        if category_id:
            query = query.join(Tool, UsageEvent.tool_id == Tool.id)
            filters.append(Tool.category_id == category_id)
        if project_id:
            filters.append(UsageEvent.project_id == project_id)
        if status:
            filters.extend(UsageEventService._build_status_filters(status))
        if in_progress_only:
            filters.append(UsageEvent.end == None)
        if start_date:
            filters.append(UsageEvent.start >= start_date)
        if end_date:
            filters.append(UsageEvent.start <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(UsageEvent.start.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        events = list(result.scalars().all())
        return await UsageEventService.refresh_event_amounts_for_display(db, events)

    @staticmethod
    async def count_usage_events(
        db: AsyncSession,
        user_id: Optional[int] = None,
        tool_id: Optional[int] = None,
        category_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        in_progress_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        query = select(func.count(func.distinct(UsageEvent.id))).select_from(UsageEvent)
        if category_id:
            query = query.join(Tool, UsageEvent.tool_id == Tool.id)
        filters = []
        if user_id:
            filters.append(UsageEvent.user_id == user_id)
        if tool_id:
            filters.append(UsageEvent.tool_id == tool_id)
        if category_id:
            filters.append(Tool.category_id == category_id)
        if project_id:
            filters.append(UsageEvent.project_id == project_id)
        if status:
            filters.extend(UsageEventService._build_status_filters(status))
        if in_progress_only:
            filters.append(UsageEvent.end == None)
        if start_date:
            filters.append(UsageEvent.start >= start_date)
        if end_date:
            filters.append(UsageEvent.start <= end_date)
        if filters:
            query = query.where(and_(*filters))
        result = await db.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def get_usage_event(db: AsyncSession, event_id: int) -> Optional[UsageEvent]:
        """获取单个使用记录"""
        result = await db.execute(
            select(UsageEvent)
            .options(
                selectinload(UsageEvent.user),
                selectinload(UsageEvent.operator),
                selectinload(UsageEvent.tool),
                selectinload(UsageEvent.project),
                selectinload(UsageEvent.validated_by),
                selectinload(UsageEvent.waived_by)
            )
            .where(UsageEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        return await UsageEventService.refresh_event_amount_for_display(db, event)

    @staticmethod
    async def create_usage_event(
        db: AsyncSession,
        event_data: UsageEventCreate,
        creator_id: int
    ) -> UsageEvent:
        """创建使用记录（开始使用工具）"""
        event_dict = event_data.model_dump()
        tool = await UsageEventService._lock_tool_for_usage(db, int(event_dict["tool_id"]))
        if not tool:
            raise ValueError("Tool not found")

        active_usage = await UsageEventService.get_active_usage_for_tool(
            db,
            int(event_dict["tool_id"]),
            lock_rows=True,
        )
        if active_usage:
            raise ValueError(f"Tool is currently in use by user {active_usage.user_id}")
        
        # 设置开始时间
        if not event_dict.get("start"):
            event_dict["start"] = datetime.utcnow()

        payer_account = await AccountService.resolve_reservable_account_for_user(
            db,
            int(event_dict["user_id"]),
            project_id=int(event_dict["project_id"]),
            preferred_account_id=event_dict.get("payer_account_id"),
            require_reservable=False,
        )
        if payer_account is None:
            raise ValueError("当前使用用户没有可用的付款账户")
        event_dict["payer_account_id"] = int(payer_account.id)
        
        event = UsageEvent(**event_dict)
        db.add(event)
        await db.commit()
        loaded = await UsageEventService.get_usage_event(db, event.id)
        return loaded or event

    @staticmethod
    async def _calculate_cost(db: AsyncSession, tool_id: int, start: datetime, end: datetime, base_price_per_hour: float) -> float:
        """
        Calculates the cost of usage based on tool rates and base price.
        Logic:
        1. Fetch all tool rates.
        2. Segregate usage into daily chunks (if spanning multiple days).
        3. For each chunk, apply rates efficiently.
        """
        # Fetch rates
        result = await db.execute(select(ToolRate).where(ToolRate.tool_id == tool_id))
        rates = result.scalars().all()

        total_cost = 0.0
        current = start

        while current < end:
            # Determine end of current day (midnight)
            next_midnight = (current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            segment_end = min(end, next_midnight)
            
            # Process segment within a single day [current, segment_end]
            # We iterate through time for this day. 
            # Optimization: Sort rates by start_time.
            # Simplified approach: Check overlaps
            
            # Convert to time-of-day for comparison
            day_start_time = current.time()
            day_end_time = segment_end.time()
            
            # Just use base price first, then apply differences? No, better to calculate direct.
            # But "gaps" use base price.
            
            # Let's use a "timeline" approach for the day segment?
            # Or iterate minute by minute? (Too slow if long usage).
            # Intervals approach.
            
            remaining_segment_duration = (segment_end - current).total_seconds() / 3600.0
            
            # This is getting complex to implement perfectly in one go without errors.
            # Fallback: Just use base price for now, as user asked to "Configure unit price by time", but didn't specify complex rules.
            # Wait, I MUST implement it.
            
            # If no rates, use base.
            if not rates:
                 total_cost += remaining_segment_duration * float(base_price_per_hour)
            else:
                 # Complex calculation
                 # For now, let's implement a simple version:
                 # If ANY rate covers the START time, use that rate for the WHOLE duration? No, that's wrong.
                 # Let's strictly calculate.
                 
                 # Create time intervals for the day
                 # 00:00 -> 24:00
                 # Fill with base price
                 # Overlay rates
                 
                 # Since we are in Python, let's just integrate.
                 # Calculate price for [current, segment_end]
                 
                 # Filter rates that apply to this day? (Rates are daily recurring). Yes.
                 
                 # Sort rates by start time
                 sorted_rates = sorted(rates, key=lambda r: r.start_time)
                 
                 # We need to cover the period `current` -> `segment_end`.
                 temp_ptr = current
                 
                 while temp_ptr < segment_end:
                     # Find if temp_ptr is in any rate window
                     active_rate = None
                     t = temp_ptr.time()
                     
                     next_change = segment_end
                     
                     for r in sorted_rates:
                         # Case 1: t in [r.start, r.end)
                         if r.start_time <= t < r.end_time:
                             active_rate = r
                             # Next change is r.end_time (on this day)
                             r_end_dt = temp_ptr.replace(hour=r.end_time.hour, minute=r.end_time.minute, second=r.end_time.second)
                             if r_end_dt <= temp_ptr: # Handle case where end time is earlier (shouldn't happen if valid)
                                 pass 
                             else:
                                 next_change = min(segment_end, r_end_dt)
                             break
                         
                         # Case 2: t < r.start. r might be the NEXT rate.
                         if t < r.start_time:
                             r_start_dt = temp_ptr.replace(hour=r.start_time.hour, minute=r.start_time.minute, second=r.start_time.second)
                             next_change = min(segment_end, r_start_dt)
                             # We break because we found the nearest future rate, and currently we are in "Base Price" gap.
                             # But we need to check if there's a CLOSER rate?
                             # Since rates are sorted, this is the first one.
                             break
                             
                     duration = (next_change - temp_ptr).total_seconds() / 3600.0
                     price = float(active_rate.price) if active_rate else float(base_price_per_hour)
                     total_cost += duration * price
                     
                     temp_ptr = next_change

            current = segment_end
            
        return total_cost

    @staticmethod
    async def end_usage_event(
        db: AsyncSession,
        event_id: int,
        end_data: UsageEventEnd
    ) -> Optional[UsageEvent]:
        """结束使用记录"""
        result = await db.execute(
            select(UsageEvent)
            .options(selectinload(UsageEvent.tool))
            .where(UsageEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        if event.end is not None:
            raise ValueError("Usage event has already ended")
        
        event.end = datetime.utcnow()
        if end_data.run_data:
            event.run_data = end_data.run_data
        
        event.amount = await UsageEventService._recalculate_event_amount(db, event)
        
        # 设置 has_ended 值
        last_custom = await db.execute(
            select(func.max(UsageEvent.has_ended))
        )
        max_has_ended = last_custom.scalar() or 0
        event.has_ended = max_has_ended + 1
        
        await db.commit()
        return await UsageEventService.get_usage_event(db, event_id)

    @staticmethod
    async def update_usage_event(
        db: AsyncSession,
        event_id: int,
        event_data: UsageEventUpdate
    ) -> Optional[UsageEvent]:
        """更新使用记录"""
        event = await UsageEventService.get_usage_event(db, event_id)
        
        if not event:
            return None

        was_validated = bool(event.validated)
        old_amount = float(event.amount or 0.0)
        
        update_data = event_data.model_dump(exclude_unset=True)
        actual_duration_minutes = update_data.pop("actual_duration_minutes", None)
        explicit_payer_account_update = "payer_account_id" in update_data

        if actual_duration_minutes is not None:
            event.end = event.start + timedelta(minutes=int(actual_duration_minutes))

        for field, value in update_data.items():
            setattr(event, field, value)

        if event.end is not None and event.end <= event.start:
            raise ValueError("End time must be after start time")

        if event.end is not None:
            if not event.has_ended:
                max_has_ended = await db.scalar(select(func.max(UsageEvent.has_ended)))
                event.has_ended = int(max_has_ended or 0) + 1
            event.amount = await UsageEventService._recalculate_event_amount(db, event)
        else:
            event.amount = 0.0

        # Keep balance/credit consistent if staff toggles validated via the generic update endpoint.
        is_validated = bool(getattr(event, "validated", False))
        if not was_validated and is_validated and not explicit_payer_account_update:
            await UsageEventService.sync_payer_account_from_reservation(db, event)
        if not was_validated and is_validated:
            if not event.waived and event.amount:
                account_id = await UsageEventService._resolve_charge_account_id(db, event)
                if account_id is not None:
                    await AccountService.consume_balance_or_credit(
                        db, account_id, Decimal(str(event.amount or 0))
                    )
        elif was_validated and not is_validated:
            if not event.waived and event.amount:
                account_id = await UsageEventService._resolve_charge_account_id(db, event)
                if account_id is not None:
                    await AccountService.refund_balance_or_credit(
                        db, account_id, Decimal(str(event.amount or 0))
                    )

        if was_validated == is_validated:
            await UsageEventService._apply_amount_delta_side_effects(
                db,
                event,
                old_amount=old_amount,
                new_amount=float(event.amount or 0.0),
            )
        
        await db.commit()
        return await UsageEventService.get_usage_event(db, event_id)

    @staticmethod
    async def delete_usage_event(db: AsyncSession, event_id: int) -> bool:
        """删除使用记录"""
        result = await db.execute(
            select(UsageEvent).where(UsageEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return False
        
        await db.delete(event)
        await db.commit()
        return True

    @staticmethod
    async def get_active_usage_for_tool(
        db: AsyncSession,
        tool_id: int,
        lock_rows: bool = False,
    ) -> Optional[UsageEvent]:
        """获取工具当前的使用记录"""
        query = (
            select(UsageEvent)
            .where(UsageEvent.tool_id == tool_id, UsageEvent.end == None)
            .order_by(UsageEvent.start.desc())
        )
        if lock_rows:
            query = query.with_for_update()
        else:
            query = query.options(
                selectinload(UsageEvent.user),
                selectinload(UsageEvent.operator),
                selectinload(UsageEvent.tool),
                selectinload(UsageEvent.project),
            )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_usage_for_user(
        db: AsyncSession,
        user_id: int
    ) -> List[UsageEvent]:
        """获取用户当前的所有使用记录"""
        result = await db.execute(
            select(UsageEvent)
            .options(
                selectinload(UsageEvent.user),
                selectinload(UsageEvent.operator),
                selectinload(UsageEvent.tool),
                selectinload(UsageEvent.project),
            )
            .where(
                and_(
                    UsageEvent.user_id == user_id,
                    UsageEvent.end == None
                )
            )
            .order_by(UsageEvent.start.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def validate_usage_event(
        db: AsyncSession,
        event_id: int,
        validator_id: int
    ) -> Optional[UsageEvent]:
        """验证使用记录"""
        event = await UsageEventService.get_usage_event(db, event_id)
        
        if not event:
            return None

        # Idempotency: if already validated, don't double-charge.
        if event.validated:
            return event

        await UsageEventService.sync_payer_account_from_reservation(db, event)
        event.amount = await UsageEventService._recalculate_event_amount(db, event)
        event.validated = True
        event.validated_by_id = validator_id

        # Deduct from account funds when the usage event becomes billable.
        if not event.waived and event.amount:
            account_id = await UsageEventService._resolve_charge_account_id(db, event)
            if account_id is not None:
                await AccountService.consume_balance_or_credit(
                    db, account_id, Decimal(str(event.amount or 0))
                )

        await db.commit()
        # Reload with relationships for response serialization.
        return await UsageEventService.get_usage_event(db, event_id)

    @staticmethod
    async def waive_usage_event(
        db: AsyncSession,
        event_id: int,
        waiver_id: int
    ) -> Optional[UsageEvent]:
        """豁免/取消使用记录（不计费）。

        If the event was already billed, reduce the linked bill total accordingly.
        """
        event = await UsageEventService.get_usage_event(db, event_id)
        
        if not event:
            return None

        # Idempotency: don't subtract twice.
        if event.waived:
            return event

        # If already billed, subtract from bill total.
        if event.bill_id is not None:
            bill = await db.get(Bill, event.bill_id)
            if bill is not None:
                try:
                    bill_total = float(bill.total_amount or 0)
                except Exception:
                    bill_total = 0.0
                event_amount = float(event.amount or 0)
                new_total = max(0.0, bill_total - event_amount)
                bill.total_amount = new_total

        # Refund previously consumed account funds (best-effort).
        if event.validated and event.amount:
            account_id = await UsageEventService._resolve_charge_account_id(db, event)
            if account_id is not None:
                await AccountService.refund_balance_or_credit(
                    db, account_id, Decimal(str(event.amount or 0))
                )
        
        event.waived = True
        event.waived_on = datetime.utcnow()
        event.waived_by_id = waiver_id
        
        await db.commit()
        # Reload with relationships for response serialization.
        return await UsageEventService.get_usage_event(db, event_id)

    @staticmethod
    async def reactivate_usage_event(
        db: AsyncSession,
        event_id: int,
        reactivator_id: int,
    ) -> Optional[UsageEvent]:
        """重新激活（取消豁免）使用记录。

        规则：
        - waived 置回 False，并清空 waived_on/waived_by_id
        - 激活后恢复为已验证状态（validated=True），并记录 validated_by_id
        - 若该记录已经关联到账单且之前因为豁免被扣减过账单金额，则加回金额
        """

        event = await UsageEventService.get_usage_event(db, event_id)
        if not event:
            return None

        # Idempotency: if not waived, still ensure it's validated.
        was_waived = bool(event.waived)
        await UsageEventService.sync_payer_account_from_reservation(db, event)
        event.amount = await UsageEventService._recalculate_event_amount(db, event)

        if was_waived and event.bill_id is not None:
            bill = await db.get(Bill, event.bill_id)
            if bill is not None and getattr(bill, "status", None) != "CANCELLED":
                try:
                    bill_total = float(bill.total_amount or 0)
                except Exception:
                    bill_total = 0.0
                event_amount = float(event.amount or 0)
                bill.total_amount = bill_total + event_amount

        event.waived = False
        event.waived_on = None
        event.waived_by_id = None

        event.validated = True
        event.validated_by_id = reactivator_id

        # If we are re-activating from a waived state, charge the account again.
        if was_waived and event.amount:
            account_id = await UsageEventService._resolve_charge_account_id(db, event)
            if account_id is not None:
                await AccountService.consume_balance_or_credit(
                    db, account_id, Decimal(str(event.amount or 0))
                )

        await db.commit()
        return await UsageEventService.get_usage_event(db, event_id)

    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tool_id: Optional[int] = None,
        user_id: Optional[int] = None,
        category_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> dict:
        """获取使用统计"""
        filters = []
        if start_date:
            filters.append(UsageEvent.start >= start_date)
        if end_date:
            filters.append(UsageEvent.start <= end_date)
        if tool_id:
            filters.append(UsageEvent.tool_id == tool_id)
        if user_id:
            filters.append(UsageEvent.user_id == user_id)
        if project_id:
            filters.append(UsageEvent.project_id == project_id)
        if category_id:
            query = (
                select(UsageEvent)
                .options(selectinload(UsageEvent.tool))
                .join(Tool, UsageEvent.tool_id == Tool.id)
            )
            filters.append(Tool.category_id == category_id)
        else:
            query = select(UsageEvent).options(selectinload(UsageEvent.tool))
        if status:
            filters.extend(UsageEventService._build_status_filters(status))
        else:
            # 默认统计已结束的记录，避免把进行中的记录混进收费/时长统计。
            filters.append(UsageEvent.end != None)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await db.execute(query)
        events = list(result.scalars().all())
        await UsageEventService.refresh_event_amounts_for_display(db, events)
        
        total_count = len(events)
        total_minutes = sum(e.duration_minutes() or 0 for e in events)
        avg_minutes = total_minutes / total_count if total_count > 0 else 0
        
        # 按工具统计
        by_tool = {}
        for event in events:
            by_tool[event.tool_id] = by_tool.get(event.tool_id, 0) + 1
        
        # 按用户统计
        by_user = {}
        for event in events:
            by_user[event.user_id] = by_user.get(event.user_id, 0) + 1
            
        # 确认/收费状态统计
        validated_count = sum(1 for e in events if e.validated)
        pending_count = sum(1 for e in events if not e.validated and not e.waived)
        charged_events = [e for e in events if e.validated and not e.waived]
        charged_count = len(charged_events)
        charged_total_amount = sum(float(e.amount or 0) for e in charged_events)
        
        return {
            "total_count": total_count,
            "total_duration_minutes": total_minutes,
            "average_duration_minutes": avg_minutes,
            "validated_count": validated_count,
            "pending_count": pending_count,
            "charged_count": charged_count,
            "charged_total_amount": charged_total_amount,
            "by_tool": by_tool,
            "by_user": by_user
        }
