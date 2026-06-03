"""staff_role — ported from security-server `role` table."""

from sqlalchemy import BigInteger, Column, String, Text

from app.db.session import Base


class StaffRole(Base):
    __tablename__ = "staff_role"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
