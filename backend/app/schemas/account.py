from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBasic

# AccountType Schemas
class AccountTypeBase(BaseModel):
    """账户类型基础模型"""
    name: str = Field(..., max_length=200, description="账户类型名称")
    display_order: int = Field(default=0, description="显示顺序")


class AccountTypeCreate(AccountTypeBase):
    """创建账户类型"""
    pass


class AccountTypeUpdate(BaseModel):
    """更新账户类型"""
    name: Optional[str] = Field(None, max_length=200)
    display_order: Optional[int] = None


class AccountTypeResponse(AccountTypeBase):
    """账户类型响应"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# Account Schemas
class AccountBase(BaseModel):
    """账户基础模型"""
    name: str = Field(..., max_length=100, description="账户名称")
    user_id: Optional[int] = Field(None, description="绑定的用户ID（每个用户一个账户）")
    note: Optional[str] = Field(None, description="备注")
    type_id: Optional[int] = Field(None, description="账户类型ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    active: bool = Field(default=True, description="是否激活")
    balance: Decimal = Field(default=Decimal("0.00"), description="账户余额")
    credit_limit: Decimal = Field(default=Decimal("0.00"), description="信用额度")
    credit_score: int = Field(default=0, description="信用值")


class AccountCreate(AccountBase):
    """创建账户"""
    member_ids: List[int] = Field(default_factory=list, description="共享成员用户ID列表")
    project_id: Optional[int] = Field(None, description="关联项目ID（内部组织账户必填）")


class AccountUpdate(BaseModel):
    """更新账户"""
    name: Optional[str] = Field(None, max_length=100)
    user_id: Optional[int] = None
    note: Optional[str] = None
    type_id: Optional[int] = None
    start_date: Optional[date] = None
    active: Optional[bool] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    credit_score: Optional[int] = None
    member_ids: Optional[List[int]] = None
    project_id: Optional[int] = None


class AccountResponse(AccountBase):
    """账户响应"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class AccountDetail(AccountResponse):
    """账户详情（包含关系）"""
    type: Optional[AccountTypeResponse] = None
    members: List[UserBasic] = Field(default_factory=list, description="共享成员")
    member_ids: List[int] = Field(default_factory=list, description="共享成员ID列表")
    default_project_id: Optional[int] = Field(None, description="默认关联项目ID（若有）")
    default_project_name: Optional[str] = Field(None, description="默认关联项目名称（若有）")
    project_binding_locked: bool = Field(False, description="是否锁定项目关联（不可编辑）")
    
    model_config = ConfigDict(from_attributes=True)


class AccountMemberUpdate(BaseModel):
    """更新账户成员"""
    user_ids: List[int] = Field(default_factory=list, description="共享成员用户ID列表")


class AccountMembershipChangeRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AccountBasic(BaseModel):
    id: int
    name: str
    active: bool
    user_id: Optional[int] = None
    type_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AccountMembershipChangeRequestCreate(BaseModel):
    target_account_id: int = Field(..., gt=0, description="目标组织账户ID")
    reason: Optional[str] = Field(None, max_length=2000, description="申请说明")


class AccountMembershipChangeRequestReview(BaseModel):
    comment: Optional[str] = Field(None, max_length=2000, description="审批备注")


class AccountMembershipChangeRequestResponse(BaseModel):
    id: int
    requester_user_id: int
    source_account_id: Optional[int] = None
    target_account_id: Optional[int] = None
    status: AccountMembershipChangeRequestStatus
    reason: Optional[str] = None
    review_comment: Optional[str] = None
    reviewer_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    requester: Optional[UserBasic] = None
    reviewer: Optional[UserBasic] = None
    source_account: Optional[AccountBasic] = None
    target_account: Optional[AccountBasic] = None

    model_config = ConfigDict(from_attributes=True)
