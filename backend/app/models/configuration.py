"""
Configuration Models
工具配置管理模型
"""
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.tool import Tool
    from app.models.user import User
    from app.models.reservation import Reservation


# Configuration maintainers many-to-many association table
configuration_maintainers = Table(
    'configuration_maintainers',
    Base.metadata,
    Column('configuration_id', Integer, ForeignKey('configuration.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
)


class Configuration(Base):
    """
    工具配置模型
    用于管理工具的各种配置选项（如激光功率、波长等）
    """
    __tablename__ = "configuration"

    # Allow legacy (pre-SQLAlchemy 2.0) type annotations during migration.
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True, comment="配置名称")
    tool_id = Column(Integer, ForeignKey("tool.id", ondelete="CASCADE"), nullable=False, comment="关联工具ID")
    
    # Configuration item details
    configurable_item_name = Column(
        String(200), 
        nullable=True, 
        comment="配置项名称（如果只有一个配置槽，可为空）"
    )
    advance_notice_limit = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="配置变更需要提前的小时数"
    )
    display_order = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="显示顺序（越小越靠前）"
    )
    
    # Configuration settings
    prompt = Column(Text, nullable=True, comment="配置提示文本")
    current_settings = Column(
        Text, 
        nullable=True,
        comment="当前配置值（多个值用逗号分隔）"
    )
    available_settings = Column(
        Text, 
        nullable=True,
        comment="可选配置值（多个值用逗号分隔）"
    )
    calendar_colors = Column(
        Text, 
        nullable=True,
        comment="日历颜色列表（HTML颜色代码，逗号分隔）"
    )
    absence_string = Column(
        String(50), 
        nullable=True,
        comment="缺失选项的显示文本"
    )
    
    # Permission and visibility settings
    qualified_users_are_maintainers = Column(
        Boolean, 
        default=False,
        comment="是否允许所有合格用户维护此配置"
    )
    exclude_from_configuration_agenda = Column(
        Boolean, 
        default=False,
        comment="是否从配置议程中排除"
    )
    enabled = Column(
        Boolean, 
        default=True,
        comment="是否启用"
    )
    
    # Relationships
    tool: "Tool" = relationship("Tool", back_populates="configurations")
    maintainers: List["User"] = relationship(
        "User",
        secondary=configuration_maintainers,
        back_populates="maintained_configurations"
    )
    history: List["ConfigurationHistory"] = relationship(
        "ConfigurationHistory",
        back_populates="configuration",
        cascade="all, delete-orphan"
    )
    options: List["ConfigurationOption"] = relationship(
        "ConfigurationOption",
        back_populates="configuration",
        foreign_keys="ConfigurationOption.configuration_id"
    )
    
    def __repr__(self):
        return f"<Configuration(id={self.id}, name='{self.name}', tool_id={self.tool_id})>"
    
    # Helper methods
    @property
    def current_settings_list(self) -> List[str]:
        """获取当前配置值列表"""
        if not self.current_settings:
            return []
        return [x.strip() for x in self.current_settings.split(",")]
    
    @property
    def available_settings_list(self) -> List[str]:
        """获取可选配置值列表"""
        if not self.available_settings:
            return []
        return [x.strip() for x in self.available_settings.split(",")]
    
    @property
    def calendar_colors_list(self) -> List[str]:
        """获取日历颜色列表"""
        if not self.calendar_colors:
            return []
        return [x.strip() for x in self.calendar_colors.split(",")]
    
    def get_current_setting(self, slot: int) -> Optional[str]:
        """获取指定槽位的当前配置值"""
        settings = self.current_settings_list
        if 0 <= slot < len(settings):
            return settings[slot]
        return None
    
    def get_color(self, setting: str) -> Optional[str]:
        """获取指定配置值的颜色"""
        if setting not in self.available_settings_list:
            return None
        index = self.available_settings_list.index(setting)
        colors = self.calendar_colors_list
        if colors and index < len(colors):
            return colors[index]
        return None
    
    @property
    def configurable_item_count(self) -> int:
        """获取可配置项的数量"""
        return len(self.current_settings_list)


class ConfigurationOption(Base):
    """
    预约配置选项模型
    用于记录预约时选择的配置选项
    """
    __tablename__ = "configuration_option"

    # Allow legacy (pre-SQLAlchemy 2.0) type annotations during migration.
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="配置选项名称")
    
    configuration_id = Column(
        Integer, 
        ForeignKey("configuration.id", ondelete="SET NULL"), 
        nullable=True,
        comment="关联的配置ID"
    )
    reservation_id = Column(
        Integer, 
        ForeignKey("reservation.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联的预约ID"
    )
    
    # Configuration option details
    current_setting = Column(
        String(200), 
        nullable=True,
        comment="当前配置值"
    )
    available_settings = Column(
        Text, 
        nullable=True,
        comment="可选配置值（多个值用逗号分隔）"
    )
    calendar_colors = Column(
        Text, 
        nullable=True,
        comment="日历颜色列表（HTML颜色代码，逗号分隔）"
    )
    absence_string = Column(
        String(50), 
        nullable=True,
        comment="缺失选项的显示文本"
    )
    
    # Relationships
    configuration: Optional["Configuration"] = relationship(
        "Configuration",
        back_populates="options",
        foreign_keys=[configuration_id]
    )
    reservation: "Reservation" = relationship(
        "Reservation",
        back_populates="configuration_options"
    )
    
    def __repr__(self):
        return f"<ConfigurationOption(id={self.id}, name='{self.name}', reservation_id={self.reservation_id})>"
    
    # Helper methods
    @property
    def available_settings_list(self) -> List[str]:
        """获取可选配置值列表"""
        if not self.available_settings:
            return []
        return [x.strip() for x in self.available_settings.split(",")]
    
    @property
    def calendar_colors_list(self) -> List[str]:
        """获取日历颜色列表"""
        if not self.calendar_colors:
            return []
        return [x.strip() for x in self.calendar_colors.split(",")]
    
    def get_color(self) -> Optional[str]:
        """获取当前配置值的颜色"""
        # If linked to configuration and settings match, use configuration's color
        if (self.configuration and 
            self.configuration.available_settings == self.available_settings):
            return self.configuration.get_color(self.current_setting)
        
        # Otherwise use own colors
        if not self.current_setting or self.current_setting not in self.available_settings_list:
            return None
        index = self.available_settings_list.index(self.current_setting)
        colors = self.calendar_colors_list
        if colors and index < len(colors):
            return colors[index]
        return None


class ConfigurationHistory(Base):
    """
    配置历史记录模型
    用于追踪配置变更历史
    """
    __tablename__ = "configuration_history"

    # Allow legacy (pre-SQLAlchemy 2.0) type annotations during migration.
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(
        Integer, 
        ForeignKey("configuration.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联的配置ID"
    )
    user_id = Column(
        Integer, 
        ForeignKey("user.id", ondelete="CASCADE"), 
        nullable=False,
        comment="操作用户ID"
    )
    modification_time = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="修改时间"
    )
    
    # Configuration change details
    item_name = Column(
        String(200), 
        nullable=True,
        comment="配置项名称"
    )
    slot = Column(
        Integer, 
        nullable=False,
        comment="槽位索引"
    )
    setting = Column(
        Text, 
        nullable=False,
        comment="配置值"
    )
    
    # Relationships
    configuration: "Configuration" = relationship(
        "Configuration",
        back_populates="history"
    )
    user: "User" = relationship(
        "User",
        back_populates="configuration_history"
    )
    
    def __repr__(self):
        return f"<ConfigurationHistory(id={self.id}, config_id={self.configuration_id}, user_id={self.user_id})>"
