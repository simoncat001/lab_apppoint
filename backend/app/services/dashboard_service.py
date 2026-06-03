from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reservation import Reservation
from app.models.task import Task
from app.models.tool import Tool
from app.models.user import User
from app.schemas.dashboard import (
    DashboardPendingTask,
    DashboardRankingItem,
    DashboardRecentReservation,
    DashboardResponse,
    DashboardStats,
    DashboardStatusBreakdown,
    DashboardTrendPoint,
    DashboardUserReport,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_report(
        self,
        current_user: User,
        current_project_id: int,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> DashboardResponse:
        now = datetime.now()
        is_admin = current_user.is_staff or current_user.is_superuser
        range_start, range_end, range_end_exclusive = self._resolve_period(
            days=days,
            start_date=start_date,
            end_date=end_date,
        )

        total_tools = await self._get_total_tools(
            is_admin=is_admin,
            current_project_id=current_project_id,
        )
        active_users = await self._get_active_users(
            current_project_id=current_project_id,
            range_start=range_start,
            range_end_exclusive=range_end_exclusive,
        )
        active_tasks, pending_tasks = await self._get_pending_tasks(
            current_user=current_user,
            is_admin=is_admin,
            current_project_id=current_project_id,
        )
        reservations = await self._get_reservations(
            current_user=current_user,
            is_admin=is_admin,
            current_project_id=current_project_id,
            range_start=range_start,
            range_end_exclusive=range_end_exclusive,
        )
        users = self._get_report_users_from_reservations(
            current_user=current_user,
            is_admin=is_admin,
            reservations=reservations,
        )

        user_reports = self._build_user_reports(users=users, reservations=reservations, now=now)
        current_user_report = user_reports.get(current_user.id) or self._empty_user_report(current_user)
        trend = self._build_trend(
            reservations=reservations,
            now=now,
            period_start=range_start.date(),
            period_end=range_end.date(),
        )
        status_breakdown = self._build_status_breakdown(
            reservations=reservations,
            now=now,
        )
        tool_rankings = self._build_rankings(
            reservations=reservations,
            entity="tool",
        )
        project_rankings = self._build_rankings(
            reservations=reservations,
            entity="project",
        )
        recent_reservations = self._build_recent_reservations(
            reservations=reservations,
            now=now,
        )

        report_rows = sorted(
            user_reports.values(),
            key=lambda row: (
                row.total_reservations == 0,
                -row.total_reservations,
                -row.total_hours,
                row.username.lower(),
            ),
        )

        stats = DashboardStats(
            total_tools=total_tools,
            active_users=active_users,
            report_users=len(report_rows),
            total_reservations=len(reservations),
            total_hours=round(
                sum(row.total_hours for row in user_reports.values()),
                2,
            ),
            active_tasks=active_tasks,
            distinct_tools=len({r.tool_id for r in reservations if r.tool_id}),
            distinct_projects=len({r.project_id for r in reservations if r.project_id}),
            ongoing_reservations=sum(row.ongoing_reservations for row in user_reports.values()),
            upcoming_reservations=sum(
                row.upcoming_reservations for row in user_reports.values()
            ),
            completed_reservations=sum(
                row.completed_reservations for row in user_reports.values()
            ),
            cancelled_reservations=sum(
                row.cancelled_reservations for row in user_reports.values()
            ),
            missed_reservations=sum(row.missed_reservations for row in user_reports.values()),
        )

        return DashboardResponse(
            scope="global" if is_admin else "personal",
            period_start=range_start.date(),
            period_end=range_end.date(),
            stats=stats,
            status_breakdown=status_breakdown,
            trend=trend,
            tool_rankings=tool_rankings,
            project_rankings=project_rankings,
            user_reports=report_rows,
            current_user_report=current_user_report,
            recent_reservations=recent_reservations,
            pending_tasks=pending_tasks,
        )

    def _resolve_period(
        self,
        days: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[datetime, datetime, datetime]:
        if start_date and end_date:
            if start_date > end_date:
                start_date, end_date = end_date, start_date
        else:
            end_date = date.today()
            start_date = end_date - timedelta(days=max(days - 1, 0))

        range_start = datetime.combine(start_date, time.min)
        range_end = datetime.combine(end_date, time.max)
        range_end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        return range_start, range_end, range_end_exclusive

    async def _get_total_tools(self, *, is_admin: bool, current_project_id: int) -> int:
        stmt = select(func.count()).select_from(Tool).where(Tool.project_id == current_project_id)
        if not is_admin:
            stmt = stmt.where(Tool.visible == True)
        return int(await self.db.scalar(stmt) or 0)

    async def _get_active_users(
        self,
        *,
        current_project_id: int,
        range_start: datetime,
        range_end_exclusive: datetime,
    ) -> int:
        return int(
            await self.db.scalar(
                select(func.count(distinct(User.id)))
                .select_from(User)
                .join(Reservation, Reservation.user_id == User.id)
                .where(
                    User.is_active == True,
                    Reservation.project_id == current_project_id,
                    Reservation.start >= range_start,
                    Reservation.start < range_end_exclusive,
                )
            )
            or 0
        )

    async def _get_pending_tasks(
        self,
        current_user: User,
        is_admin: bool,
        current_project_id: int,
    ) -> tuple[int, list[DashboardPendingTask]]:
        filters = [
            Task.cancelled == False,
            Task.resolved == False,
            Tool.project_id == current_project_id,
        ]
        if not is_admin:
            filters.append(Task.creator_id == current_user.id)

        total = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Task)
                .join(Tool, Tool.id == Task.tool_id)
                .where(*filters)
            )
            or 0
        )

        pending_q = (
            select(Task)
            .options(selectinload(Task.tool), selectinload(Task.creator))
            .join(Tool, Tool.id == Task.tool_id)
            .where(*filters)
            .order_by(Task.creation_time.desc())
            .limit(6)
        )
        pending_tasks = (await self.db.execute(pending_q)).scalars().all()

        rows = [
            DashboardPendingTask(
                creator_name=self._user_display_name(getattr(task, "creator", None)),
                tool_name=(task.tool.name if getattr(task, "tool", None) else None),
                problem_description=task.problem_description,
                urgency=int(task.urgency),
                creation_time=self._normalize_datetime(task.creation_time),
            )
            for task in pending_tasks
        ]
        return total, rows

    def _get_report_users_from_reservations(
        self,
        *,
        current_user: User,
        is_admin: bool,
        reservations: list[Reservation],
    ) -> list[User]:
        if not is_admin:
            return [current_user]

        users_by_id: dict[int, User] = {}
        for reservation in reservations:
            user = getattr(reservation, "user", None)
            if user is None:
                continue
            users_by_id[int(user.id)] = user

        return sorted(
            users_by_id.values(),
            key=lambda user: (
                not bool(user.is_active),
                not bool(user.is_staff),
                str(user.username or "").lower(),
            ),
        )

    async def _get_reservations(
        self,
        current_user: User,
        is_admin: bool,
        current_project_id: int,
        range_start: datetime,
        range_end_exclusive: datetime,
    ) -> list[Reservation]:
        filters = [
            Reservation.project_id == current_project_id,
            Reservation.start >= range_start,
            Reservation.start < range_end_exclusive,
        ]
        if not is_admin:
            filters.append(Reservation.user_id == current_user.id)

        query = (
            select(Reservation)
            .options(
                selectinload(Reservation.user),
                selectinload(Reservation.tool),
                selectinload(Reservation.project),
            )
            .where(*filters)
            .order_by(Reservation.start.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    def _build_user_reports(
        self,
        users: list[User],
        reservations: list[Reservation],
        now: datetime,
    ) -> Dict[int, DashboardUserReport]:
        reports = {user.id: self._empty_user_report(user) for user in users}
        tool_counters: dict[int, Counter[str]] = defaultdict(Counter)
        tool_sets: dict[int, set[int]] = defaultdict(set)
        project_sets: dict[int, set[int]] = defaultdict(set)

        for reservation in reservations:
            user = reservation.user
            if not user:
                continue

            report = reports.get(user.id)
            if report is None:
                report = self._empty_user_report(user)
                reports[user.id] = report

            status = self._reservation_status(reservation, now)
            duration_hours = self._reservation_duration_hours(reservation)

            report.total_reservations += 1
            report.total_hours = round(report.total_hours + duration_hours, 2)

            if status == "ongoing":
                report.ongoing_reservations += 1
            elif status == "completed":
                report.completed_reservations += 1
            elif status == "upcoming":
                report.upcoming_reservations += 1
            elif status == "cancelled":
                report.cancelled_reservations += 1
            elif status == "missed":
                report.missed_reservations += 1

            if reservation.tool_id:
                tool_sets[user.id].add(int(reservation.tool_id))
            if reservation.project_id:
                project_sets[user.id].add(int(reservation.project_id))

            tool_name = reservation.tool.name if getattr(reservation, "tool", None) else None
            if tool_name:
                tool_counters[user.id][tool_name] += 1

            start_dt = self._normalize_datetime(reservation.start)
            if start_dt:
                if (
                    report.latest_reservation_at is None
                    or start_dt > report.latest_reservation_at
                ):
                    report.latest_reservation_at = start_dt

                if start_dt >= now and (
                    report.next_reservation_at is None
                    or start_dt < report.next_reservation_at
                ):
                    report.next_reservation_at = start_dt

        for user_id, report in reports.items():
            report.distinct_tools = len(tool_sets[user_id])
            report.distinct_projects = len(project_sets[user_id])
            favorite = tool_counters[user_id].most_common(1)
            report.favorite_tool_name = favorite[0][0] if favorite else None
            report.total_hours = round(report.total_hours, 2)

        return reports

    def _build_trend(
        self,
        reservations: list[Reservation],
        now: datetime,
        period_start: date,
        period_end: date,
    ) -> list[DashboardTrendPoint]:
        buckets: dict[date, Counter[str]] = defaultdict(Counter)
        cursor = period_start
        while cursor <= period_end:
            buckets[cursor]
            cursor += timedelta(days=1)

        for reservation in reservations:
            bucket = self._normalize_datetime(reservation.start)
            if bucket is None:
                continue
            bucket_date = bucket.date()
            if bucket_date < period_start or bucket_date > period_end:
                continue

            status = self._reservation_status(reservation, now)
            buckets[bucket_date]["total"] += 1
            buckets[bucket_date][status] += 1

        return [
            DashboardTrendPoint(
                date=day,
                total=counts["total"],
                ongoing=counts["ongoing"],
                completed=counts["completed"],
                upcoming=counts["upcoming"],
                cancelled=counts["cancelled"],
                missed=counts["missed"],
            )
            for day, counts in sorted(buckets.items(), key=lambda item: item[0])
        ]

    def _build_status_breakdown(
        self,
        reservations: list[Reservation],
        now: datetime,
    ) -> list[DashboardStatusBreakdown]:
        counts = Counter(self._reservation_status(reservation, now) for reservation in reservations)
        order = [
            ("ongoing", "进行中"),
            ("upcoming", "未开始"),
            ("completed", "已完成"),
            ("cancelled", "已取消"),
            ("missed", "已失约"),
        ]
        return [
            DashboardStatusBreakdown(key=key, label=label, count=counts.get(key, 0))
            for key, label in order
        ]

    def _build_rankings(
        self,
        reservations: list[Reservation],
        *,
        entity: str,
    ) -> list[DashboardRankingItem]:
        aggregate: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {"reservation_count": 0, "total_hours": 0.0}
        )

        for reservation in reservations:
            if entity == "tool":
                name = reservation.tool.name if getattr(reservation, "tool", None) else "未分配仪器"
            else:
                name = (
                    reservation.project.name
                    if getattr(reservation, "project", None)
                    else "未分配项目"
                )

            aggregate[name]["reservation_count"] += 1
            aggregate[name]["total_hours"] += self._reservation_duration_hours(reservation)

        items = [
            DashboardRankingItem(
                name=name,
                reservation_count=int(values["reservation_count"]),
                total_hours=round(float(values["total_hours"]), 2),
            )
            for name, values in aggregate.items()
        ]

        items.sort(
            key=lambda item: (
                -item.reservation_count,
                -item.total_hours,
                item.name.lower(),
            )
        )
        return items[:8]

    def _build_recent_reservations(
        self,
        reservations: list[Reservation],
        now: datetime,
    ) -> list[DashboardRecentReservation]:
        rows = []
        for reservation in reservations[:8]:
            rows.append(
                DashboardRecentReservation(
                    user_name=self._user_display_name(getattr(reservation, "user", None)),
                    tool_name=(
                        reservation.tool.name if getattr(reservation, "tool", None) else None
                    ),
                    project_name=(
                        reservation.project.name
                        if getattr(reservation, "project", None)
                        else None
                    ),
                    start=self._normalize_datetime(reservation.start),
                    end=self._normalize_datetime(reservation.end),
                    status=self._reservation_status(reservation, now),
                )
            )
        return rows

    def _empty_user_report(self, user: User) -> DashboardUserReport:
        return DashboardUserReport(
            user_id=int(user.id),
            username=user.username,
            full_name=self._user_display_name(user),
            is_active=bool(user.is_active),
            is_staff=bool(user.is_staff or user.is_superuser),
            is_verified=bool(getattr(user, "is_verified", False)),
            total_reservations=0,
            ongoing_reservations=0,
            completed_reservations=0,
            upcoming_reservations=0,
            cancelled_reservations=0,
            missed_reservations=0,
            total_hours=0.0,
            distinct_tools=0,
            distinct_projects=0,
            favorite_tool_name=None,
            latest_reservation_at=None,
            next_reservation_at=None,
        )

    @staticmethod
    def _user_display_name(user: User | None) -> str:
        if user is None:
            return "未知用户"

        first_name = (getattr(user, "first_name", None) or "").strip()
        last_name = (getattr(user, "last_name", None) or "").strip()
        full_name = f"{last_name}{first_name}".strip()
        if full_name:
            return full_name
        return getattr(user, "username", None) or "未知用户"

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    def _reservation_duration_hours(self, reservation: Reservation) -> float:
        start = self._normalize_datetime(reservation.start)
        end = self._normalize_datetime(reservation.end)
        if start is None or end is None or end <= start:
            return 0.0
        return max((end - start).total_seconds() / 3600, 0.0)

    def _reservation_status(self, reservation: Reservation, now: datetime) -> str:
        if reservation.cancelled:
            return "cancelled"
        if reservation.missed:
            return "missed"

        start = self._normalize_datetime(reservation.start)
        end = self._normalize_datetime(reservation.end)

        if start and end:
            if start <= now <= end:
                return "ongoing"
            if now < start:
                return "upcoming"
        return "completed"
