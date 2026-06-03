"""Port of `UserServiceImpl`."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.staff_security import md5_hash, md5_matches
from app.models.staff import StaffUser
from app.services.staff.permission_service import PermissionService
from app.services.staff.result import StaffBusinessError


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = value.strip()
    return s or None


class StaffUserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permissions = PermissionService(db)

    # --------------------------------------------------------------- auth
    async def get_by_username(self, username: str) -> Optional[StaffUser]:
        if not username:
            return None
        result = await self.db.execute(select(StaffUser).where(StaffUser.username == username))
        return result.scalar_one_or_none()

    async def verify_password(self, user: StaffUser, password: str) -> bool:
        return bool(user) and md5_matches(password, user.password)

    # ------------------------------------------------------------ register
    async def register(self, *, username: str, password: str, name: Optional[str], email: Optional[str], phone: Optional[str]) -> StaffUser:
        username = _strip(username) or ""
        password = password or ""
        name = _strip(name)
        email = _strip(email)
        phone = _strip(phone)

        if not username:
            raise StaffBusinessError("用户名不能为空")
        if not (3 <= len(username) <= 64):
            raise StaffBusinessError("用户名长度需在 3-64 个字符之间")
        if not password:
            raise StaffBusinessError("密码不能为空")
        if not (6 <= len(password) <= 128):
            raise StaffBusinessError("密码长度需在 6-128 个字符之间")
        if username.lower() == "admin":
            raise StaffBusinessError("该用户名不可注册")

        if await self._username_exists(username):
            raise StaffBusinessError("用户名已存在")
        if email and await self._email_exists(email):
            raise StaffBusinessError("邮箱已存在")
        if phone and await self._phone_exists(phone):
            raise StaffBusinessError("手机号已存在")

        user = StaffUser(
            username=username,
            password=md5_hash(password),
            name=name or username,
            email=email,
            phone=phone,
            status=0,  # awaiting approval
            job_number=None,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ----------------------------------------------------------------- CRUD
    async def create_user(self, *, actor_id: int, payload: dict) -> StaffUser:
        if not await self.permissions.is_super_admin(actor_id):
            raise StaffBusinessError("无权限创建用户")

        job_number = _strip(payload.get("job_number"))
        if job_number and await self._job_number_exists(job_number):
            raise StaffBusinessError(f"工号 {job_number} 已存在")

        raw_password = payload.get("password") or ""
        password_hash = md5_hash(raw_password) if raw_password else md5_hash("123456")

        user = StaffUser(
            username=_strip(payload.get("username")) or "",
            password=password_hash,
            name=_strip(payload.get("name")),
            email=_strip(payload.get("email")),
            phone=_strip(payload.get("phone")),
            job_number=job_number,
            status=int(payload.get("status") or 1),
        )
        if not user.username:
            raise StaffBusinessError("用户名不能为空")
        if await self._username_exists(user.username):
            raise StaffBusinessError("用户名已存在")

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(self, *, actor_id: int, payload: dict) -> StaffUser:
        target_id = payload.get("id")
        if target_id is None:
            raise StaffBusinessError("用户ID不能为空")
        target_id = int(target_id)
        is_self = actor_id == target_id
        if not is_self and not await self.permissions.is_super_admin(actor_id):
            raise StaffBusinessError("无权限修改其他用户信息")

        user = await self.db.get(StaffUser, target_id)
        if user is None:
            raise StaffBusinessError("用户不存在")

        job_number = _strip(payload.get("job_number"))
        if job_number is not None and job_number != (user.job_number or None):
            if await self._job_number_exists(job_number, exclude_id=target_id):
                raise StaffBusinessError(f"工号 {job_number} 已存在")
            user.job_number = job_number

        for field in ("name", "email", "phone"):
            if field in payload and payload[field] is not None:
                setattr(user, field, _strip(payload[field]))
        if "status" in payload and payload["status"] is not None:
            user.status = int(payload["status"])

        raw_password = payload.get("password")
        if raw_password:
            user.password = md5_hash(raw_password)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, *, actor_id: int, target_id: int) -> bool:
        if not await self.permissions.is_super_admin(actor_id):
            raise StaffBusinessError("无权限删除用户")
        user = await self.db.get(StaffUser, target_id)
        if user is None:
            return False
        await self.db.delete(user)
        await self.db.commit()
        return True

    async def get_user(self, user_id: int) -> Optional[StaffUser]:
        user = await self.db.get(StaffUser, user_id)
        if user is not None:
            user.password = None  # mirror Spring's getById behaviour
        return user

    async def list_users(self, *, keyword: Optional[str], page_num: int, page_size: int, enabled: bool) -> Tuple[List[StaffUser], int]:
        base = select(StaffUser).where(StaffUser.username != "admin")
        if keyword:
            like = f"%{keyword}%"
            base = base.where(or_(StaffUser.name.ilike(like), StaffUser.job_number.ilike(like)))

        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        stmt = base.order_by(StaffUser.id.desc())
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        for u in rows:
            u.password = None
        return list(rows), int(total or 0)

    # ------------------------------------------------------------ helpers
    async def _username_exists(self, username: str) -> bool:
        return await self._scalar_count(StaffUser.username == username)

    async def _email_exists(self, email: str) -> bool:
        return await self._scalar_count(StaffUser.email == email)

    async def _phone_exists(self, phone: str) -> bool:
        return await self._scalar_count(StaffUser.phone == phone)

    async def _job_number_exists(self, job_number: str, *, exclude_id: Optional[int] = None) -> bool:
        stmt = select(func.count()).select_from(StaffUser).where(StaffUser.job_number == job_number)
        if exclude_id is not None:
            stmt = stmt.where(StaffUser.id != exclude_id)
        return int((await self.db.execute(stmt)).scalar_one() or 0) > 0

    async def _scalar_count(self, *where) -> bool:
        stmt = select(func.count()).select_from(StaffUser)
        for clause in where:
            stmt = stmt.where(clause)
        return int((await self.db.execute(stmt)).scalar_one() or 0) > 0
