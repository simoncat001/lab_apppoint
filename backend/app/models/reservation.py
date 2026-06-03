"""
Reservation model - SQLAlchemy ORM
"""
from typing import TYPE_CHECKING, List
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.configuration import ConfigurationOption


class Reservation(Base):
    """预约模型"""
    __tablename__ = "reservation"

    # Allow legacy (pre-SQLAlchemy 2.0) type annotations during migration.
    __allow_unmapped__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Missing columns
    # creation_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    # title = Column(Text, default="", nullable=False)
    short_notice = Column(Boolean, default=False, nullable=False)
    
    # 
    # 用户和工具
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    tool_id = Column(Integer, ForeignKey("tool.id"), nullable=True, index=True)
    # descendant_id = Column(Integer, ForeignKey("reservation.id"), nullable=True)
    # area_id = Column(Integer, ForeignKey("area.id"), nullable=True, index=True)
    area_id = Column(Integer, nullable=True, index=True)
    
    # 项目
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False, index=True)
    # 付款账户（预约人账户，和项目收款账户解耦）
    payer_account_id = Column(Integer, ForeignKey("account.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 时间
    start = Column(DateTime(timezone=True), nullable=False, index=True)
    end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 状态
    cancelled = Column(Boolean, default=False, nullable=False)
    cancellation_time = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    missed = Column(Boolean, default=False, nullable=False)
    
    # 备注
    additional_information = Column(Text, default="")
    self_configuration = Column(Boolean, default=False, nullable=False)

    # 支付信息
    payment_status = Column(String(20), default="UNPAID", nullable=False)  # UNPAID/PAID
    payment_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    payment_method = Column(String(50), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # 实际完成填报
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    completion_note = Column(Text, nullable=True)
    completed_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 缩短标志
    shortened = Column(Boolean, default=False, nullable=False)
    
    # 问题回答（JSON格式）
    question_data = Column(Text, nullable=True)

    # 关系 - User / Tool / Project
    user = relationship("User", foreign_keys=[user_id])
    tool = relationship("Tool", foreign_keys=[tool_id])
    project = relationship("Project", foreign_keys=[project_id])
    payer_account: "Account" = relationship("Account", foreign_keys=[payer_account_id])
    creator = relationship("User", foreign_keys=[creator_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    
    # 关系 - ConfigurationOption
    configuration_options: List["ConfigurationOption"] = relationship(
        "ConfigurationOption",
        back_populates="reservation",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Reservation(id={self.id}, tool_id={self.tool_id}, user_id={self.user_id})>"
