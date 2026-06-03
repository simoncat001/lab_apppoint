"""staff_user_role — ported from `user_role` join table."""

from sqlalchemy import BigInteger, Column, UniqueConstraint

from app.db.session import Base


class StaffUserRole(Base):
    __tablename__ = "staff_user_role"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_staff_user_role"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    role_id = Column(BigInteger, nullable=False, index=True)
