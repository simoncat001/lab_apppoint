from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.bill import Bill
    from app.models.user import User


# Account members many-to-many association table
account_members = Table(
    "account_members",
    Base.metadata,
    Column("account_id", Integer, ForeignKey("account.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class AccountType(Base):
    """账户类型分类"""
    __tablename__ = "account_type"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    display_order: Mapped[int] = mapped_column(default=0)

    # 关系
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="type")

    def __repr__(self):
        return f"<AccountType(id={self.id}, name='{self.name}')>"


class Account(Base):
    """账户模型 - 用于项目资金管理"""
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # One account per user (treat user as account)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
        index=True,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 外键
    type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("account_type.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 字段
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    balance: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.00, nullable=False, comment="账户余额"
    )
    credit_limit: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.00, nullable=False, comment="信用额度（余额不足时透支额度）"
    )
    credit_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="信用值"
    )

    # 关系
    type: Mapped[Optional["AccountType"]] = relationship("AccountType", back_populates="accounts")
    user: Mapped[Optional["User"]] = relationship("User")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="account")
    bills: Mapped[List["Bill"]] = relationship("Bill", back_populates="account")
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary=account_members,
        back_populates="shared_accounts",
    )

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', active={self.active})>"

    def display_with_status(self) -> str:
        """显示带状态的账户名称"""
        prefix = "[INACTIVE] " if not self.active else ""
        return f"{prefix}{self.name}"

    @property
    def member_ids(self) -> List[int]:
        """成员用户ID列表（用于序列化）"""
        if not self.members:
            return []
        return [member.id for member in self.members]


class AccountMembershipChangeRequest(Base):
    """用户组织账户加入申请（需管理员审批）"""

    __tablename__ = "account_membership_change_request"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )
    source_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_user_id])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_user_id])
    source_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[source_account_id]
    )
    target_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[target_account_id]
    )

    def __repr__(self):
        return (
            f"<AccountMembershipChangeRequest(id={self.id}, requester_user_id={self.requester_user_id}, "
            f"status='{self.status}')>"
        )
