from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.project import Project
    from app.models.tool import Tool
    from app.models.user import User


class UsageEvent(Base):
    """工具使用记录模型"""
    __tablename__ = "usage_event"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 外键
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    operator_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True
    )
    tool_id: Mapped[int] = mapped_column(
        ForeignKey("tool.id", ondelete="CASCADE"),
        index=True
    )
    validated_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True
    )
    waived_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # 时间字段
    start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # 费用
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, comment="费用金额")
    
    # 账单
    bill_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bill.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    payer_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # 状态字段
    has_ended: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_work: Mapped[bool] = mapped_column(Boolean, default=False)
    training: Mapped[bool] = mapped_column(Boolean, default=False)
    waived: Mapped[bool] = mapped_column(Boolean, default=False)
    waived_on: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 文本字段
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pre_run_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_id])
    project: Mapped["Project"] = relationship("Project")
    tool: Mapped["Tool"] = relationship("Tool")
    validated_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[validated_by_id]
    )
    waived_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[waived_by_id]
    )
    payer_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[payer_account_id]
    )

    def __repr__(self):
        return f"<UsageEvent(id={self.id}, tool_id={self.tool_id}, start={self.start})>"

    def self_usage(self) -> bool:
        """检查是否为自己使用"""
        return self.user_id == self.operator_id

    def duration_minutes(self) -> Optional[int]:
        """计算使用时长（分钟）"""
        if not self.end or not self.start:
            return None
        delta = self.end - self.start
        return int(delta.total_seconds() // 60)

    @property
    def is_in_progress(self) -> bool:
        """是否正在使用中"""
        return self.end is None
