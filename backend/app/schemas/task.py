from datetime import datetime
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskUrgencyEnum(IntEnum):
    """任务紧急程度"""
    LOW = -1
    NORMAL = 0
    HIGH = 1


class TaskCategoryStageEnum(IntEnum):
    """任务分类阶段"""
    INITIAL_ASSESSMENT = 0
    COMPLETION = 1


# TaskCategory Schemas
class TaskCategoryBase(BaseModel):
    """任务分类基础模型"""
    name: str = Field(..., max_length=100, description="分类名称")
    stage: TaskCategoryStageEnum = Field(..., description="阶段")


class TaskCategoryCreate(TaskCategoryBase):
    """创建任务分类"""
    pass


class TaskCategoryUpdate(BaseModel):
    """更新任务分类"""
    name: Optional[str] = Field(None, max_length=100)
    stage: Optional[TaskCategoryStageEnum] = None


class TaskCategoryResponse(TaskCategoryBase):
    """任务分类响应"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# Task Schemas
class TaskBase(BaseModel):
    """任务基础模型"""
    tool_id: int = Field(..., description="工具ID")
    urgency: TaskUrgencyEnum = Field(..., description="紧急程度")
    force_shutdown: bool = Field(default=False, description="是否强制关闭工具")
    safety_hazard: bool = Field(default=False, description="是否安全隐患")
    problem_description: Optional[str] = Field(None, description="问题描述")
    problem_category_id: Optional[int] = Field(None, description="问题分类ID")


class TaskCreate(TaskBase):
    """创建任务"""
    pass


class TaskUpdate(BaseModel):
    """更新任务"""
    urgency: Optional[TaskUrgencyEnum] = None
    force_shutdown: Optional[bool] = None
    safety_hazard: Optional[bool] = None
    problem_description: Optional[str] = None
    progress_description: Optional[str] = None
    problem_category_id: Optional[int] = None
    estimated_resolution_time: Optional[datetime] = None


class TaskResolve(BaseModel):
    """解决任务"""
    resolution_description: str = Field(..., description="解决方案描述")
    resolution_category_id: Optional[int] = Field(None, description="解决方案分类ID")


class TaskCancel(BaseModel):
    """取消任务"""
    resolution_description: str = Field(..., description="取消原因")


class TaskResponse(TaskBase):
    """任务响应"""
    id: int
    creator_id: int
    creation_time: datetime
    last_updated: Optional[datetime] = None
    last_updated_by_id: Optional[int] = None
    estimated_resolution_time: Optional[datetime] = None
    cancelled: bool
    resolved: bool
    resolution_time: Optional[datetime] = None
    resolver_id: Optional[int] = None
    resolution_description: Optional[str] = None
    resolution_category_id: Optional[int] = None
    progress_description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaskDetail(TaskResponse):
    """任务详情（包含关系）"""
    status_display: str
    
    model_config = ConfigDict(from_attributes=True)


# TaskHistory Schemas
class TaskHistoryBase(BaseModel):
    """任务历史基础模型"""
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., max_length=200, description="状态描述")


class TaskHistoryCreate(TaskHistoryBase):
    """创建任务历史"""
    pass


class TaskHistoryResponse(TaskHistoryBase):
    """任务历史响应"""
    id: int
    user_id: int
    time: datetime
    
    model_config = ConfigDict(from_attributes=True)
