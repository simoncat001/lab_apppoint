"""
Tool Pydantic schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ToolProject(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ToolBase(BaseModel):
    """工具基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    visible: bool = True
    operational: bool = False
    requires_reservation: bool = True
    description: str = ""
    image: str = ""
    location: Optional[str] = None
    phone_number: Optional[str] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    price_type: int = 1
    price_per_use: float = 0
    price_per_hour: float = 0
    maximum_reservations_per_day: Optional[int] = None
    restrict_external_access: bool = False


class ToolImage(BaseModel):
    id: int
    tool_id: int
    path: str
    sort_order: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ToolCreate(ToolBase):
    """创建工具"""
    primary_owner_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class ToolUpdate(BaseModel):
    """更新工具"""
    name: Optional[str] = None
    visible: Optional[bool] = None
    operational: Optional[bool] = None
    requires_reservation: Optional[bool] = None
    description: Optional[str] = None
    location: Optional[str] = None
    price_type: Optional[int] = None
    price_per_use: Optional[float] = None
    price_per_hour: Optional[float] = None
    maximum_reservations_per_day: Optional[int] = None
    phone_number: Optional[str] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    restrict_external_access: Optional[bool] = None


class ToolInDB(ToolBase):
    """数据库中的工具"""
    id: int
    _primary_owner_id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Tool(ToolInDB):
    """返回给客户端的工具"""
    category: Optional["ToolCategory"] = None
    project: Optional[ToolProject] = None
    tags: List["ToolTag"] = Field(default_factory=list)
    images: List["ToolImage"] = Field(default_factory=list)


class ToolCategoryBase(BaseModel):
    name: str


class ToolCategoryCreate(ToolCategoryBase):
    pass


class ToolCategory(ToolCategoryBase):
    id: int

    class Config:
        from_attributes = True


class ToolTagBase(BaseModel):
    name: str


class ToolTagCreate(ToolTagBase):
    pass


class ToolTag(ToolTagBase):
    id: int

    class Config:
        from_attributes = True


class ToolAdmin(BaseModel):
    id: int
    username: str
    first_name: str = ""
    last_name: str = ""

    class Config:
        from_attributes = True


class ToolAdminUpdate(BaseModel):
    user_ids: List[int] = Field(default_factory=list)


class ToolEnable(BaseModel):
    """启用工具请求"""
    user_id: int = Field(..., description="使用用户ID")
    project_id: Optional[int] = Field(None, description="项目ID（不传则使用仪器绑定项目）")
    operator_id: Optional[int] = Field(None, description="操作员ID（如果不传则为当前用户）")
    note: Optional[str] = None


class ToolDisable(BaseModel):
    """禁用工具请求"""
    note: Optional[str] = None
    run_data: Optional[str] = None


class ToolProjectSuggestRequest(BaseModel):
    """仪器项目智能归属建议请求"""
    name: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    description: Optional[str] = None


class ToolProjectSuggestCandidate(BaseModel):
    project_id: int
    project_name: str
    score: int
    reason: str


class ToolProjectSuggestResponse(BaseModel):
    matched: bool
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    score: int = 0
    reason: str = ""
    candidates: List[ToolProjectSuggestCandidate] = Field(default_factory=list)


class ToolUserAccessGrant(BaseModel):
    """授权用户使用仪器"""
    user_id: int


class ToolUserAccessInfo(BaseModel):
    """仪器用户授权信息"""
    id: int
    tool_id: int
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    granted_by: Optional[int] = None
    granted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
