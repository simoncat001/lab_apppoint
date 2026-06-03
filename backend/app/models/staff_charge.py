from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class StaffCharge(Base):
    """员工收费记录模型 - 记录员工为客户提供服务的收费信息"""
    __tablename__ = "staff_charge"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 外键 - 员工和客户
    staff_member_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True
    )
    
    # 验证和豁免相关
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
    waived_on: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 状态字段
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 费用与账单
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    bill_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bill.id", ondelete="SET NULL"),
        nullable=True
    )

    waived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 文本字段
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系
    staff_member: Mapped["User"] = relationship(
        "User",
        foreign_keys=[staff_member_id],
        back_populates="staff_charges_given"
    )
    customer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[customer_id],
        back_populates="staff_charges_received"
    )
    project: Mapped["Project"] = relationship("Project")
    validated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[validated_by_id]
    )
    waived_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[waived_by_id]
    )

    def __repr__(self):
        return f"<StaffCharge(id={self.id}, staff={self.staff_member_id}, customer={self.customer_id})>"

    def duration_minutes(self) -> Optional[int]:
        """计算服务时长（分钟）"""
        if not self.end or not self.start:
            return None
        delta = self.end - self.start
        return int(delta.total_seconds() // 60)

    @property
    def is_in_progress(self) -> bool:
        """是否正在进行中"""
        return self.end is None

    @property
    def is_billable(self) -> bool:
        """是否可计费（未豁免）"""
        return not self.waived
