"""
User service layer
"""

import secrets
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr, TypeAdapter
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from app.services.security_server_project_service import SecurityServerProjectService

EMAIL_ADAPTER = TypeAdapter(EmailStr)
SECURITY_SERVER_EMAIL_DOMAIN = "security-server.matai.com"


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """获取单个用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user:
            # Fetch password from local_auth
            from sqlalchemy import text
            auth_result = await self.db.execute(
                text("SELECT hashed_password FROM local_auth WHERE user_id = :uid"),
                {"uid": user.id}
            )
            auth_row = auth_result.fetchone()
            if auth_row:
                user.hashed_password = auth_row[0]
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """通过手机号获取用户"""
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_in: UserCreate) -> User:
        """创建用户"""
        hashed = get_password_hash(user_in.password)
        user = User(
            username=user_in.username,
            email=user_in.email,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            password=hashed,
            is_active=user_in.is_active,
            is_staff=user_in.is_staff,
            is_superuser=user_in.is_superuser,
            badge_number=user_in.badge_number,
            phone_number=user_in.phone_number,
            auth_source=user_in.auth_source or "local",
            priority_reservation=user_in.priority_reservation,
            special_course_access=user_in.special_course_access,
        )
        if user_in.managed_tool_ids:
            user.managed_tool_ids_list = user_in.managed_tool_ids
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Insert password into local_auth
        await self.db.execute(
            text("INSERT INTO local_auth (user_id, hashed_password) VALUES (:uid, :pwd)"),
            {"uid": user.id, "pwd": hashed}
        )
        await self.db.commit()

        return user

    async def get_or_create_security_server_user(self, remote_user_info: dict) -> User:
        """Upsert local mirror user from security-server user info and return local user."""
        username = str(remote_user_info.get("username") or "").strip()
        if not username:
            raise ValueError("Security server user info missing username")

        user = await self.get_user_by_username(username)
        remote_name = str(remote_user_info.get("name") or username).strip() or username
        first_name, last_name = self._split_name(remote_name)
        email = self._normalize_security_email(remote_user_info, username)
        phone = str(remote_user_info.get("phone") or "").strip() or None
        badge_number = self._parse_security_badge_number(remote_user_info.get("jobNumber"))
        badge_number = await self._dedupe_badge_number(badge_number, user_id=user.id if user else None)
        email = await self._dedupe_email_for_security_user(email, username, user_id=user.id if user else None)
        permission_snapshot = await SecurityServerProjectService.get_permission_snapshot_for_username_from_db(
            self.db,
            username=username,
        )

        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone
            user.is_active = (remote_user_info.get("status", 1) != 0)
            user.is_verified = True
            user.is_staff = permission_snapshot.is_admin
            user.is_superuser = permission_snapshot.is_super_admin
            user.auth_source = "security_server"
            if badge_number is not None:
                user.badge_number = badge_number
            await self.db.commit()
            await self.db.refresh(user)
            return user

        placeholder_password = get_password_hash(secrets.token_urlsafe(32))
        status_val = remote_user_info.get("status")
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=placeholder_password,
            is_active=(status_val != 0),
            is_verified=True,
            is_staff=permission_snapshot.is_admin,
            is_superuser=permission_snapshot.is_super_admin,
            badge_number=badge_number,
            phone_number=phone,
            auth_source="security_server",
            priority_reservation=False,
            special_course_access=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(self, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """更新用户"""
        user = await self.get_user(user_id)
        if not user:
            return None

        update_data = user_in.model_dump(exclude_unset=True)

        # 如果更新密码，需要哈希
        if "password" in update_data:
            new_password = update_data.pop("password")
            hashed = get_password_hash(new_password)
            update_data["hashed_password"] = hashed
            # Keep local_auth in sync for authentication
            await self._upsert_local_auth(user_id, hashed)
        
        for field, value in update_data.items():
            if field == "managed_tool_ids":
                user.managed_tool_ids_list = value or []
            else:
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_user(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.commit()

        # 级联清理该用户在 media/users/{id}/ 下的头像等媒体文件
        from app.core.media import remove_entity_dir
        remove_entity_dir("users", user_id)
        return True
    
    async def update_last_login(self, user_id: int) -> None:
        """更新最后登录时间"""
        user = await self.get_user(user_id)
        if user:
            user.last_login = datetime.utcnow()
            await self.db.commit()

    async def update_password(self, user_id: int, new_password: str) -> None:
        """更新用户密码并同步到 local_auth"""
        hashed = get_password_hash(new_password)
        await self._upsert_local_auth(user_id, hashed)
        user = await self.get_user(user_id)
        if user:
            user.password = hashed
        await self.db.commit()

    async def _upsert_local_auth(self, user_id: int, hashed_password: str) -> None:
        """插入或更新 local_auth 表"""
        result = await self.db.execute(
            text("SELECT hashed_password FROM local_auth WHERE user_id = :uid"),
            {"uid": user_id},
        )
        row = result.fetchone()
        if row:
            await self.db.execute(
                text("UPDATE local_auth SET hashed_password = :pwd WHERE user_id = :uid"),
                {"uid": user_id, "pwd": hashed_password},
            )
        else:
            await self.db.execute(
                text("INSERT INTO local_auth (user_id, hashed_password) VALUES (:uid, :pwd)"),
                {"uid": user_id, "pwd": hashed_password},
            )

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        cleaned = (name or "").strip()
        if not cleaned:
            return "User", "User"
        if " " in cleaned:
            parts = [part for part in cleaned.split() if part]
            if len(parts) >= 2:
                return " ".join(parts[1:])[:100], parts[0][:100]
        if len(cleaned) >= 2:
            return cleaned[1:101], cleaned[:1]
        return cleaned[:100], cleaned[:100]

    @staticmethod
    def _parse_security_badge_number(raw_value) -> Optional[int]:
        if raw_value is None:
            return None
        value = str(raw_value).strip()
        if not value.isdigit():
            return None
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _normalize_security_email(remote_user_info: dict, username: str) -> str:
        email = str(remote_user_info.get("email") or "").strip()
        if email:
            try:
                return str(EMAIL_ADAPTER.validate_python(email))
            except Exception:
                pass
        safe_username = "".join(ch for ch in username if ch.isalnum() or ch in {".", "_", "-"}).strip()
        if not safe_username:
            safe_username = "user"
        return f"{safe_username}@{SECURITY_SERVER_EMAIL_DOMAIN}"

    async def _dedupe_badge_number(self, badge_number: Optional[int], *, user_id: Optional[int]) -> Optional[int]:
        if badge_number is None:
            return None
        existing = await self.db.execute(
            select(User.id).where(User.badge_number == badge_number)
        )
        row = existing.first()
        if not row:
            return badge_number
        existing_id = int(row[0])
        if user_id is not None and existing_id == user_id:
            return badge_number
        return None

    async def _dedupe_email_for_security_user(
        self,
        email: str,
        username: str,
        *,
        user_id: Optional[int],
    ) -> str:
        candidate = email
        suffix = 0
        while True:
            result = await self.db.execute(select(User.id).where(User.email == candidate))
            row = result.first()
            if not row:
                return candidate
            existing_id = int(row[0])
            if user_id is not None and existing_id == user_id:
                return candidate
            suffix += 1
            local_part, _, domain = email.partition("@")
            base_local = local_part or username or "user"
            candidate = f"{base_local}+sec{suffix}@{domain or SECURITY_SERVER_EMAIL_DOMAIN}"
