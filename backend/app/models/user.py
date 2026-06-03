"""User model - SQLAlchemy ORM.

This project uses SQLAlchemy 2.0; relationship attributes must be annotated with
Mapped[...] (or the model must opt out via __allow_unmapped__).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.staff_charge import StaffCharge
    from app.models.configuration import Configuration, ConfigurationHistory
    from app.models.account import Account


class User(Base):
    """用户模型"""
    __tablename__ = "user"
    __allow_unmapped__ = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Mapped to 'password' column in DB to satisfy NOT NULL constraint
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    # Legacy alias for compatibility if needed
    @property
    def hashed_password(self):
        return self.password

    @hashed_password.setter
    def hashed_password(self, value):
        self.password = value
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    badge_number: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    access_expiration: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    phone_number: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    auth_source: Mapped[str] = mapped_column(
        String(30),
        default="local",
        nullable=False,
        index=True,
        comment="认证来源: local/security_server",
    )
    priority_reservation: Mapped[bool] = mapped_column(Boolean, default=False)
    special_course_access: Mapped[bool] = mapped_column(Boolean, default=False)
    managed_tool_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    date_joined: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 关系 - StaffCharge
    staff_charges_given: Mapped[list["StaffCharge"]] = relationship(
        "StaffCharge",
        foreign_keys="StaffCharge.staff_member_id",
        back_populates="staff_member"
    )
    staff_charges_received: Mapped[list["StaffCharge"]] = relationship(
        "StaffCharge",
        foreign_keys="StaffCharge.customer_id",
        back_populates="customer"
    )
    
    # 关系 - Configuration
    maintained_configurations: Mapped[list["Configuration"]] = relationship(
        "Configuration",
        secondary="configuration_maintainers",
        back_populates="maintainers"
    )
    configuration_history: Mapped[list["ConfigurationHistory"]] = relationship(
        "ConfigurationHistory",
        back_populates="user"
    )

    # 关系 - Account (shared organization accounts)
    shared_accounts: Mapped[list["Account"]] = relationship(
        "Account",
        secondary="account_members",
        back_populates="members"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    @property
    def managed_tool_ids_list(self) -> list[int]:
        if not self.managed_tool_ids:
            return []
        return [int(item) for item in self.managed_tool_ids.split(",") if item.strip().isdigit()]

    @managed_tool_ids_list.setter
    def managed_tool_ids_list(self, value: list[int]):
        if not value:
            self.managed_tool_ids = None
        else:
            self.managed_tool_ids = ",".join(str(item) for item in value)
