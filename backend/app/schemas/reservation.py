"""
Reservation Pydantic schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ReservationUser(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class ReservationTool(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ReservationProject(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ReservationBase(BaseModel):
    """预约基础模型"""
    tool_id: Optional[int] = None
    area_id: Optional[int] = None
    project_id: Optional[int] = None
    payer_account_id: Optional[int] = None
    start: datetime
    end: datetime
    additional_information: str = ""
    self_configuration: bool = False
    payment_status: Optional[str] = None
    payment_amount: Optional[float] = None
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    completion_note: Optional[str] = None
    completed_by_id: Optional[int] = None
    completed_at: Optional[datetime] = None


class ReservationCreate(ReservationBase):
    """创建预约"""
    user_id: int


class ReservationUpdate(BaseModel):
    """更新预约"""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    payer_account_id: Optional[int] = None
    additional_information: Optional[str] = None
    cancelled: Optional[bool] = None
    payment_status: Optional[str] = None
    payment_amount: Optional[float] = None
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    completion_note: Optional[str] = None
    completed_by_id: Optional[int] = None
    completed_at: Optional[datetime] = None


class ReservationInDB(ReservationBase):
    """数据库中的预约"""
    id: int
    user_id: int
    cancelled: bool = False
    missed: bool = False
    
    class Config:
        from_attributes = True


class Reservation(ReservationInDB):
    """返回给客户端的预约"""
    user: Optional[ReservationUser] = None
    tool: Optional[ReservationTool] = None
    project: Optional[ReservationProject] = None


class ReservationOccupiedSlot(BaseModel):
    """仪器已占用时间段"""
    id: int
    start: datetime
    end: datetime

    class Config:
        from_attributes = True


class ReservationPaymentRequest(BaseModel):
    amount: Optional[float] = None
    method: Optional[str] = None


class ReservationCompletionRequest(BaseModel):
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    completion_note: Optional[str] = None
