from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import MaintenanceRecord
from app.models.tool import Tool
from app.schemas.maintenance import MaintenanceRecordCreate, MaintenanceRecordUpdate


class MaintenanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_records(
        self,
        tool_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> List[MaintenanceRecord]:
        query = select(MaintenanceRecord).options(
            selectinload(MaintenanceRecord.tool),
            selectinload(MaintenanceRecord.staff),
        )
        if project_id is not None:
            query = query.join(Tool, Tool.id == MaintenanceRecord.tool_id).where(Tool.project_id == project_id)
        if tool_id is not None:
            query = query.where(MaintenanceRecord.tool_id == tool_id)
        result = await self.db.execute(query.order_by(MaintenanceRecord.performed_at.desc()))
        return result.scalars().all()

    async def get_record(self, record_id: int) -> Optional[MaintenanceRecord]:
        result = await self.db.execute(
            select(MaintenanceRecord)
            .options(
                selectinload(MaintenanceRecord.tool),
                selectinload(MaintenanceRecord.staff),
            )
            .where(MaintenanceRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def create_record(self, data: MaintenanceRecordCreate, staff_id: int) -> MaintenanceRecord:
        record = MaintenanceRecord(
            tool_id=data.tool_id,
            performed_at=data.performed_at or datetime.utcnow(),
            next_due_at=data.next_due_at,
            description=data.description,
            staff_id=staff_id,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_record(self, record_id: int, data: MaintenanceRecordUpdate) -> Optional[MaintenanceRecord]:
        record = await self.get_record(record_id)
        if not record:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete_record(self, record_id: int) -> bool:
        record = await self.get_record(record_id)
        if not record:
            return False
        await self.db.delete(record)
        await self.db.commit()
        return True
