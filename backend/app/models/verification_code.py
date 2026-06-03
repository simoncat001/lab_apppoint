"""
Verification code model - SQLAlchemy ORM
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from app.db.session import Base


class VerificationCode(Base):
    """验证码记录"""
    __tablename__ = "verification_code"

    id = Column(Integer, primary_key=True, index=True)
    target = Column(String(200), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)  # email/phone
    purpose = Column(String(20), nullable=False)  # register/login
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<VerificationCode(id={self.id}, target='{self.target}', purpose='{self.purpose}')>"
