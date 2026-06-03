from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StaffChargeBase(BaseModel):
    """员工收费基础模型"""
    staff_member_id: int = Field(..., description="员工ID")
    customer_id: int = Field(..., description="客户ID")
    project_id: int = Field(..., description="项目ID")
    note: Optional[str] = Field(None, description="备注")


class StaffChargeCreate(StaffChargeBase):
    """创建员工收费记录"""
    start: Optional[datetime] = Field(None, description="开始时间（默认当前时间）")


class StaffChargeUpdate(BaseModel):
    """更新员工收费记录"""
    end: Optional[datetime] = Field(None, description="结束时间")
    note: Optional[str] = None
    validated: Optional[bool] = Field(None, description="是否已验证")
    validated_by_id: Optional[int] = Field(None, description="验证人ID")


class StaffChargeEnd(BaseModel):
    """结束员工收费记录"""
    note: Optional[str] = Field(None, description="结束备注")


class StaffChargeResponse(StaffChargeBase):
    """员工收费响应"""
    id: int
    start: datetime
    end: Optional[datetime] = None
    validated: bool
    validated_by_id: Optional[int] = None
    waived: bool
    waived_on: Optional[datetime] = None
    waived_by_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class StaffChargeDetail(StaffChargeResponse):
    """员工收费详情（包含关系）"""
    duration_minutes: Optional[int] = None
    is_in_progress: bool = False
    is_billable: bool = True
    
    model_config = ConfigDict(from_attributes=True)


class StaffChargeStats(BaseModel):
    """员工收费统计"""
    total_count: int
    total_duration_minutes: int
    average_duration_minutes: float
    by_staff: dict[int, int]  # staff_member_id -> count
    by_customer: dict[int, int]  # customer_id -> count
    by_project: dict[int, int]  # project_id -> count
    total_billable: int
    total_waived: int
