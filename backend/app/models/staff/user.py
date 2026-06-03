"""staff_user — ported from security-server `user` table.

Schema source: V1.0.0__init_schema.sql + V1.0.1__add_job_number.sql
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from app.db.session import Base


class StaffUser(Base):
    __tablename__ = "staff_user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    job_number = Column(String(50), nullable=True, unique=True)
    status = Column(Integer, nullable=False, default=1, comment="1:active 0:pending/disabled")
    created_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
