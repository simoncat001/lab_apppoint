"""
Tool model - SQLAlchemy ORM
"""
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.tool_tag_link import tool_tag_link

if TYPE_CHECKING:
    from app.models.configuration import Configuration
    from app.models.project import Project
    from app.models.tool_image import ToolImage
    from app.models.tool_user_access import ToolUserAccess


class Tool(Base):
    """工具模型"""
    __tablename__ = "tool"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_tool_project_name"),
    )

    # Allow legacy (pre-SQLAlchemy 2.0) type annotations during migration.
    __allow_unmapped__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    visible = Column(Boolean, default=True, nullable=False)
    operational = Column(Boolean, default=False, nullable=False)
    
    _primary_owner_id = Column("primary_owner_id", Integer, ForeignKey("user.id"))
    _location = Column("location", String(100), nullable=True)
    _phone_number = Column("phone_number", String(40), nullable=True)
    
    # 预留和使用设置
    _requires_area_access_id = Column("requires_area_access_id", Integer, nullable=True)
    grant_physical_access_level_upon_qualification_id = Column(Integer, nullable=True)
    grant_badge_reader_access_upon_qualification = Column(String(100), nullable=True)
    
    # 工具配置
    reservation_horizon = Column(Integer, default=14, nullable=True)
    requires_reservation = Column(Boolean, default=True, nullable=False)
    minimum_usage_block_time = Column(Integer, nullable=True)
    maximum_usage_block_time = Column(Integer, nullable=True)
    maximum_reservations_per_day = Column(Integer, nullable=True)
    minimum_time_between_reservations = Column(Integer, nullable=True)
    maximum_future_reservation_time = Column(Integer, nullable=True)
    missed_reservation_threshold = Column(Integer, nullable=True)
    
    # 工具描述
    description = Column(Text, default="")
    serial = Column(String(100), nullable=True)
    
    # 策略设置
    policy_off_between_times = Column(Boolean, default=False, nullable=False)
    policy_off_weekend = Column(Boolean, default=False, nullable=False)
    image = Column(String(200), default="", nullable=False)
    tool_calendar_color = Column(String(50), default="#3788d8", nullable=False)
    qualifications_never_expire = Column(Boolean, default=False, nullable=False)
    ask_to_leave_area_when_done_using = Column(Boolean, default=False, nullable=False)
    restrict_external_access = Column(Boolean, default=False, nullable=False,
                                      comment="启用后外部用户需单独授权才能使用此仪器")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True, index=True)
    _operation_mode = Column("_operation_mode", Integer, default=0, nullable=False)
    abuse_weight = Column(Integer, default=1, nullable=False)
    problem_shutdown_enabled = Column(Boolean, default=False, nullable=False)
    
    # 互锁信息
    interlock_id = Column(Integer, nullable=True)
    
    # 收费配置
    # 0: 按次收费 (Per Use), 1: 按时收费 (Per Hour/Time)
    price_type = Column(Integer, default=1, nullable=False, comment="收费类型: 0=按次, 1=按时")
    price_per_use = Column(Numeric(10, 2), default=0.00, nullable=False, comment="每次使用价格")
    price_per_hour = Column(Numeric(10, 2), default=0.00, nullable=False, comment="每小时价格")

    # 分类
    category_id = Column(Integer, ForeignKey("tool_category.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 关系 - Configuration
    configurations: List["Configuration"] = relationship(
        "Configuration",
        back_populates="tool",
        cascade="all, delete-orphan"
    )

    category = relationship("ToolCategory", back_populates="tools")
    project: "Project" = relationship("Project")
    tags = relationship(
        "ToolTag",
        secondary=tool_tag_link,
        back_populates="tools",
    )
    images: List["ToolImage"] = relationship(
        "ToolImage",
        back_populates="tool",
        cascade="all, delete-orphan",
        order_by="ToolImage.sort_order, ToolImage.id",
    )

    # 关系 - ToolUserAccess (设备级用户权限)
    authorized_users: List["ToolUserAccess"] = relationship(
        "ToolUserAccess",
        back_populates="tool",
        cascade="all, delete-orphan",
    )

    # 关系 - ToolRate
    rates: List["ToolRate"] = relationship(
        "ToolRate",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Tool(id={self.id}, name='{self.name}')>"

    # -------------------- Attribute aliases (API-facing) --------------------
    # The database columns are mapped to underscored attributes to preserve
    # legacy naming. Pydantic's `from_attributes` expects public attribute names
    # like `location` and `phone_number`, so expose them here.

    @property
    def primary_owner_id(self):
        return self._primary_owner_id

    @primary_owner_id.setter
    def primary_owner_id(self, value):
        self._primary_owner_id = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def phone_number(self):
        return self._phone_number

    @phone_number.setter
    def phone_number(self, value):
        self._phone_number = value

"""NOTE:

Tool categories now use a dedicated `tool_category` table.
"""
