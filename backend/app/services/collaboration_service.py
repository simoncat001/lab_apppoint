"""Service layer for research collaboration records."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tool_permissions import can_manage_tool
from app.models.collaboration import CollaborationRecord
from app.models.user import User
from app.schemas.collaboration import CollaborationRecordCreate, CollaborationRecordUpdate


REGULAR_RECORD_TYPES = {"tool_note", "reservation_note", "experiment_note", "issue"}
KNOWLEDGE_RECORD_TYPES = {"maintenance_experience", "sop", "faq", "case_study"}
MANAGER_ONLY_RECORD_TYPES = KNOWLEDGE_RECORD_TYPES


class CollaborationPermissionError(PermissionError):
    """Raised when the current user cannot perform an action."""


class CollaborationStateError(ValueError):
    """Raised when a requested state transition is invalid."""


class CollaborationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _with_author(stmt):
        return stmt.options(selectinload(CollaborationRecord.author))

    @staticmethod
    def _is_superuser(user: User | object | None) -> bool:
        return bool(getattr(user, "is_superuser", False))

    @staticmethod
    def _is_staff(user: User | object | None) -> bool:
        return bool(getattr(user, "is_staff", False))

    @classmethod
    def _is_record_manager(cls, user: User | object | None, record: CollaborationRecord | object) -> bool:
        if user is None:
            return False
        if cls._is_superuser(user) or cls._is_staff(user):
            return True
        return can_manage_tool(user, getattr(record, "tool_id", None))

    @staticmethod
    def _is_author(user: User | object | None, record: CollaborationRecord | object) -> bool:
        return user is not None and int(getattr(user, "id", 0) or 0) == int(getattr(record, "author_id", 0) or 0)

    @classmethod
    def ensure_can_create(cls, user: User | object, record: CollaborationRecord | object) -> None:
        record_type = str(getattr(record, "record_type", "") or "")
        if record_type in REGULAR_RECORD_TYPES:
            return
        if record_type in MANAGER_ONLY_RECORD_TYPES and cls._is_record_manager(user, record):
            return
        raise CollaborationPermissionError("Not authorized to create this collaboration record type")

    @classmethod
    def ensure_can_read(cls, user: User | object, record: CollaborationRecord | object) -> None:
        if getattr(record, "deleted_at", None) is not None:
            raise CollaborationPermissionError("Record has been deleted")
        if cls._is_record_manager(user, record) or cls._is_author(user, record):
            return

        visibility = str(getattr(record, "visibility", "") or "")
        if visibility == "project":
            return
        if visibility == "staff" and (cls._is_staff(user) or cls._is_superuser(user)):
            return
        if visibility == "tool_managers" and can_manage_tool(user, getattr(record, "tool_id", None)):
            return

        raise CollaborationPermissionError("Not authorized to read this collaboration record")

    @classmethod
    def ensure_can_update(cls, user: User | object, record: CollaborationRecord | object) -> None:
        if cls._is_record_manager(user, record):
            return
        if cls._is_author(user, record):
            if str(getattr(record, "status", "") or "") == "archived":
                raise CollaborationPermissionError("Archived records can only be edited by staff or tool managers")
            if str(getattr(record, "record_type", "") or "") in REGULAR_RECORD_TYPES:
                return
        raise CollaborationPermissionError("Not authorized to update this collaboration record")

    @classmethod
    def ensure_can_delete(cls, user: User | object, record: CollaborationRecord | object) -> None:
        if cls._is_record_manager(user, record) or cls._is_author(user, record):
            return
        raise CollaborationPermissionError("Not authorized to delete this collaboration record")

    @classmethod
    def ensure_can_publish(cls, user: User | object, record: CollaborationRecord | object) -> None:
        if str(getattr(record, "status", "") or "") != "draft":
            raise CollaborationStateError("Only draft records can be published")

        record_type = str(getattr(record, "record_type", "") or "")
        if record_type in KNOWLEDGE_RECORD_TYPES:
            if cls._is_record_manager(user, record):
                return
            raise CollaborationPermissionError("Only staff or tool managers can publish knowledge records")

        if record_type in REGULAR_RECORD_TYPES:
            if cls._is_record_manager(user, record) or cls._is_author(user, record):
                return
            raise CollaborationPermissionError("Not authorized to publish this collaboration record")

        if cls._is_record_manager(user, record):
            return
        raise CollaborationPermissionError("Only staff or tool managers can publish this collaboration record type")

    @classmethod
    def ensure_can_archive(cls, user: User | object, record: CollaborationRecord | object) -> None:
        if str(getattr(record, "status", "") or "") != "published":
            raise CollaborationStateError("Only published records can be archived")
        cls.ensure_can_delete(user, record)

    @classmethod
    def _apply_read_scope(cls, stmt, user: User | object):
        if cls._is_staff(user) or cls._is_superuser(user):
            return stmt
        return stmt.where(
            or_(
                CollaborationRecord.visibility == "project",
                CollaborationRecord.author_id == int(getattr(user, "id", 0) or 0),
            )
        )

    @staticmethod
    def _apply_filters(
        stmt,
        *,
        project_id: int,
        tool_id: Optional[int],
        reservation_id: Optional[int],
        record_type: Optional[str],
        status: Optional[str],
        visibility: Optional[str],
        keyword: Optional[str],
        author_id: Optional[int] = None,
    ):
        stmt = stmt.where(
            CollaborationRecord.project_id == project_id,
            CollaborationRecord.deleted_at.is_(None),
        )
        if tool_id is not None:
            stmt = stmt.where(CollaborationRecord.tool_id == tool_id)
        if reservation_id is not None:
            stmt = stmt.where(CollaborationRecord.reservation_id == reservation_id)
        if record_type:
            stmt = stmt.where(CollaborationRecord.record_type == record_type)
        if status:
            stmt = stmt.where(CollaborationRecord.status == status)
        if visibility:
            stmt = stmt.where(CollaborationRecord.visibility == visibility)
        if author_id is not None:
            stmt = stmt.where(CollaborationRecord.author_id == author_id)
        if keyword:
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(CollaborationRecord.title.like(like), CollaborationRecord.content.like(like)))
        return stmt

    async def create_record(
        self,
        payload: CollaborationRecordCreate,
        *,
        project_id: int,
        author_id: int,
        current_user: User,
        tool_id: Optional[int] = None,
    ) -> CollaborationRecord:
        record = CollaborationRecord(
            project_id=project_id,
            tool_id=tool_id if tool_id is not None else payload.tool_id,
            reservation_id=payload.reservation_id,
            author_id=author_id,
            record_type=payload.record_type,
            title=payload.title,
            content=payload.content,
            content_format=payload.content_format,
            visibility=payload.visibility,
            status=payload.status,
            pinned=False,
        )
        self.ensure_can_create(current_user, record)
        if record.status == "published":
            record.status = "draft"
            self.ensure_can_publish(current_user, record)
            record.status = "published"
        if record.status == "archived":
            raise CollaborationStateError("Records cannot be created directly as archived")

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["author"])
        return record

    async def get_record(self, record_id: int, *, project_id: int) -> Optional[CollaborationRecord]:
        result = await self.db.execute(
            self._with_author(select(CollaborationRecord)).where(
                CollaborationRecord.id == record_id,
                CollaborationRecord.project_id == project_id,
                CollaborationRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        *,
        project_id: int,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        tool_id: Optional[int] = None,
        reservation_id: Optional[int] = None,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
        visibility: Optional[str] = None,
        keyword: Optional[str] = None,
        author_id: Optional[int] = None,
    ) -> Sequence[CollaborationRecord]:
        stmt = self._with_author(select(CollaborationRecord))
        stmt = self._apply_filters(
            stmt,
            project_id=project_id,
            tool_id=tool_id,
            reservation_id=reservation_id,
            record_type=record_type,
            status=status,
            visibility=visibility,
            keyword=keyword,
            author_id=author_id,
        )
        stmt = self._apply_read_scope(stmt, current_user)
        stmt = stmt.order_by(
            CollaborationRecord.pinned.desc(),
            CollaborationRecord.created_at.desc(),
            CollaborationRecord.id.desc(),
        )
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_records(
        self,
        *,
        project_id: int,
        current_user: User,
        tool_id: Optional[int] = None,
        reservation_id: Optional[int] = None,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
        visibility: Optional[str] = None,
        keyword: Optional[str] = None,
        author_id: Optional[int] = None,
    ) -> int:
        stmt = select(func.count(CollaborationRecord.id))
        stmt = self._apply_filters(
            stmt,
            project_id=project_id,
            tool_id=tool_id,
            reservation_id=reservation_id,
            record_type=record_type,
            status=status,
            visibility=visibility,
            keyword=keyword,
            author_id=author_id,
        )
        stmt = self._apply_read_scope(stmt, current_user)
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def update_record(
        self,
        record: CollaborationRecord,
        payload: CollaborationRecordUpdate,
        *,
        current_user: User,
    ) -> CollaborationRecord:
        self.ensure_can_update(current_user, record)
        changes = payload.model_dump(exclude_unset=True)
        next_status = changes.get("status")
        if next_status == "published" and record.status != "published":
            self.ensure_can_publish(current_user, record)
        if next_status == "archived" and record.status != "archived":
            self.ensure_can_archive(current_user, record)
        for field, value in changes.items():
            setattr(record, field, value)
        record.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["author"])
        return record

    async def soft_delete_record(self, record: CollaborationRecord, *, current_user: User) -> CollaborationRecord:
        self.ensure_can_delete(current_user, record)
        record.deleted_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["author"])
        return record

    async def publish_record(self, record: CollaborationRecord, *, current_user: User) -> CollaborationRecord:
        self.ensure_can_publish(current_user, record)
        record.status = "published"
        record.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["author"])
        return record

    async def archive_record(self, record: CollaborationRecord, *, current_user: User) -> CollaborationRecord:
        self.ensure_can_archive(current_user, record)
        record.status = "archived"
        record.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record, attribute_names=["author"])
        return record
