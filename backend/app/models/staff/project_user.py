"""staff_project_user — ported from `project_user` join table."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, UniqueConstraint

from app.db.session import Base


class StaffProjectUser(Base):
    __tablename__ = "staff_project_user"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uk_staff_project_user"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    join_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    type = Column(Integer, nullable=False, default=0, comment="0:member 1:admin")
