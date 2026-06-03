from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.usage_event import UsageEventResponse
from app.schemas.user import UserBasic

# Shared properties
class BillBase(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = "DRAFT"

# Properties to receive on creation
class BillCreate(BillBase):
    account_id: int
    force_regenerate: bool = False # If true, cancels existing bills for period

# Properties to return to client
class BillResponse(BillBase):
    id: int
    account_id: int
    account_name: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    reference_number: str
    issued_date: datetime
    total_amount: Decimal
    
    class Config:
        from_attributes = True

class BillDetailResponse(BillResponse):
    """账单详情：包含关联使用记录与用户基础信息"""

    user: Optional[UserBasic] = None
    usage_events: List[UsageEventResponse] = []

    class Config:
        from_attributes = True

class BillGenerationRequest(BaseModel):
    account_ids: Optional[List[int]] = None  # If None, all accounts


class BillUpdate(BaseModel):
    """管理员编辑账单"""
    due_date: Optional[datetime] = None
    status: Optional[str] = None
