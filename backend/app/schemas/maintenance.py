from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MaintenanceRecordBase(BaseModel):
    tool_id: int
    performed_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    description: str


class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass


class MaintenanceRecordUpdate(BaseModel):
    performed_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    description: Optional[str] = None


class MaintenanceRecordResponse(MaintenanceRecordBase):
    id: int
    staff_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
