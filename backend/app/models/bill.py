from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy import inspect
from sqlalchemy.orm import relationship
from sqlalchemy.orm.state import NO_VALUE
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.usage_event import UsageEvent
    from app.models.staff_charge import StaffCharge

class Bill(Base):
    """账单模型"""
    __tablename__ = "bill"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=False, index=True)
    
    reference_number = Column(String(100), unique=True, nullable=False, index=True)
    
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    issued_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    
    total_amount = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default="DRAFT", index=True) # DRAFT, ISSUED, PAID, CANCELLED
    
    # 关系
    account = relationship("Account", back_populates="bills")
    
    # 关联的收费项目
    usage_events = relationship("UsageEvent", backref="bill") # Backref simple approach
    staff_charges = relationship("StaffCharge", backref="bill")
    # NOTE: Consumables module removed.

    @property
    def user_id(self) -> Optional[int]:
        state = inspect(self)
        if state.attrs.account.loaded_value is NO_VALUE:
            return None
        if self.account is None:
            return None
        return self.account.user_id

    @property
    def username(self) -> Optional[str]:
        state = inspect(self)
        if state.attrs.account.loaded_value is NO_VALUE:
            return None
        if self.account is None:
            return None
        account_state = inspect(self.account)
        if account_state.attrs.user.loaded_value is NO_VALUE:
            return None
        if self.account.user is None:
            return None
        return self.account.user.username

    @property
    def account_name(self) -> Optional[str]:
        """Account display name (supports organization accounts without bound user)."""
        state = inspect(self)
        if state.attrs.account.loaded_value is NO_VALUE:
            return None
        if self.account is None:
            return None
        return self.account.name

    def __repr__(self):
        return f"<Bill(id={self.id}, ref={self.reference_number}, amount={self.total_amount})>"
