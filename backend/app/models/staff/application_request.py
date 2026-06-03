"""staff_application_request — ported from `application_request` table.

Approval flow for users joining a department / project / group.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, Text

from app.db.session import Base


class StaffApplicationRequest(Base):
    __tablename__ = "staff_application_request"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    target_type = Column(Integer, nullable=False, comment="1:department 2:project 3:group")
    target_id = Column(BigInteger, nullable=False, index=True)
    status = Column(Integer, nullable=False, default=0, comment="0:pending 1:approved 2:rejected")
    reason = Column(Text, nullable=True)
    approver_id = Column(BigInteger, nullable=True)
    approve_result = Column(Integer, nullable=True, comment="1:approved 2:rejected")
    created_time = Column(DateTime, nullable=False, default=datetime.utcnow)
