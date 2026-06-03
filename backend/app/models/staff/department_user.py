"""staff_department_user — ported from `department_user` join table."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, UniqueConstraint

from app.db.session import Base


class StaffDepartmentUser(Base):
    __tablename__ = "staff_department_user"
    __table_args__ = (
        UniqueConstraint("department_id", "user_id", name="uk_staff_dept_user"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    department_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    join_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    type = Column(Integer, nullable=False, default=0, comment="0:member 1:admin")
