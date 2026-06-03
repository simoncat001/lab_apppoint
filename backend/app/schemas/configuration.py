"""
Configuration Pydantic schemas
工具配置管理 Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ==================== Configuration Schemas ====================

class ConfigurationBase(BaseModel):
    """配置基础模型"""
    name: str = Field(..., description="配置名称", max_length=200)
    tool_id: int = Field(..., description="关联工具ID")
    configurable_item_name: Optional[str] = Field(None, description="配置项名称", max_length=200)
    advance_notice_limit: int = Field(0, description="提前通知限制（小时）", ge=0)
    display_order: int = Field(0, description="显示顺序", ge=0)
    prompt: Optional[str] = Field(None, description="配置提示文本")
    current_settings: Optional[str] = Field(None, description="当前配置值（逗号分隔）")
    available_settings: Optional[str] = Field(None, description="可选配置值（逗号分隔）")
    calendar_colors: Optional[str] = Field(None, description="日历颜色列表（逗号分隔）")
    absence_string: Optional[str] = Field(None, description="缺失选项显示文本", max_length=50)
    qualified_users_are_maintainers: bool = Field(False, description="合格用户是否为维护人员")
    exclude_from_configuration_agenda: bool = Field(False, description="是否从配置议程中排除")
    enabled: bool = Field(True, description="是否启用")


class ConfigurationCreate(ConfigurationBase):
    """创建配置请求"""
    maintainer_ids: Optional[List[int]] = Field(default_factory=list, description="维护人员ID列表")


class ConfigurationUpdate(BaseModel):
    """更新配置请求"""
    name: Optional[str] = Field(None, description="配置名称", max_length=200)
    configurable_item_name: Optional[str] = Field(None, description="配置项名称", max_length=200)
    advance_notice_limit: Optional[int] = Field(None, description="提前通知限制（小时）", ge=0)
    display_order: Optional[int] = Field(None, description="显示顺序", ge=0)
    prompt: Optional[str] = Field(None, description="配置提示文本")
    current_settings: Optional[str] = Field(None, description="当前配置值（逗号分隔）")
    available_settings: Optional[str] = Field(None, description="可选配置值（逗号分隔）")
    calendar_colors: Optional[str] = Field(None, description="日历颜色列表（逗号分隔）")
    absence_string: Optional[str] = Field(None, description="缺失选项显示文本", max_length=50)
    qualified_users_are_maintainers: Optional[bool] = Field(None, description="合格用户是否为维护人员")
    exclude_from_configuration_agenda: Optional[bool] = Field(None, description="是否从配置议程中排除")
    enabled: Optional[bool] = Field(None, description="是否启用")
    maintainer_ids: Optional[List[int]] = Field(None, description="维护人员ID列表")


class ConfigurationResponse(ConfigurationBase):
    """配置响应模型"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class ConfigurationDetail(ConfigurationResponse):
    """配置详情模型（包含计算属性）"""
    current_settings_list: List[str] = Field(default_factory=list, description="当前配置值列表")
    available_settings_list: List[str] = Field(default_factory=list, description="可选配置值列表")
    calendar_colors_list: List[str] = Field(default_factory=list, description="日历颜色列表")
    configurable_item_count: int = Field(0, description="可配置项数量")
    maintainer_ids: List[int] = Field(default_factory=list, description="维护人员ID列表")
    history_count: int = Field(0, description="历史记录数量")


class ConfigurationChangeSetting(BaseModel):
    """修改配置设置请求"""
    slot: int = Field(..., description="槽位索引", ge=0)
    choice: int = Field(..., description="选择项索引", ge=0)


# ==================== ConfigurationOption Schemas ====================

class ConfigurationOptionBase(BaseModel):
    """配置选项基础模型"""
    name: str = Field(..., description="配置选项名称", max_length=200)
    configuration_id: Optional[int] = Field(None, description="关联的配置ID")
    reservation_id: int = Field(..., description="关联的预约ID")
    current_setting: Optional[str] = Field(None, description="当前配置值", max_length=200)
    available_settings: Optional[str] = Field(None, description="可选配置值（逗号分隔）")
    calendar_colors: Optional[str] = Field(None, description="日历颜色列表（逗号分隔）")
    absence_string: Optional[str] = Field(None, description="缺失选项显示文本", max_length=50)


class ConfigurationOptionCreate(ConfigurationOptionBase):
    """创建配置选项请求"""
    pass


class ConfigurationOptionUpdate(BaseModel):
    """更新配置选项请求"""
    name: Optional[str] = Field(None, description="配置选项名称", max_length=200)
    current_setting: Optional[str] = Field(None, description="当前配置值", max_length=200)
    available_settings: Optional[str] = Field(None, description="可选配置值（逗号分隔）")
    calendar_colors: Optional[str] = Field(None, description="日历颜色列表（逗号分隔）")
    absence_string: Optional[str] = Field(None, description="缺失选项显示文本", max_length=50)


class ConfigurationOptionResponse(ConfigurationOptionBase):
    """配置选项响应模型"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class ConfigurationOptionDetail(ConfigurationOptionResponse):
    """配置选项详情模型（包含计算属性）"""
    available_settings_list: List[str] = Field(default_factory=list, description="可选配置值列表")
    calendar_colors_list: List[str] = Field(default_factory=list, description="日历颜色列表")
    color: Optional[str] = Field(None, description="当前配置值的颜色")


# ==================== ConfigurationHistory Schemas ====================

class ConfigurationHistoryBase(BaseModel):
    """配置历史基础模型"""
    configuration_id: int = Field(..., description="关联的配置ID")
    user_id: int = Field(..., description="操作用户ID")
    modification_time: str = Field(..., description="修改时间")
    item_name: Optional[str] = Field(None, description="配置项名称", max_length=200)
    slot: int = Field(..., description="槽位索引", ge=0)
    setting: str = Field(..., description="配置值")


class ConfigurationHistoryCreate(BaseModel):
    """创建配置历史请求"""
    configuration_id: int = Field(..., description="关联的配置ID")
    slot: int = Field(..., description="槽位索引", ge=0)
    setting: str = Field(..., description="配置值")
    item_name: Optional[str] = Field(None, description="配置项名称", max_length=200)


class ConfigurationHistoryResponse(ConfigurationHistoryBase):
    """配置历史响应模型"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class ConfigurationHistoryDetail(ConfigurationHistoryResponse):
    """配置历史详情模型"""
    configuration_name: Optional[str] = Field(None, description="配置名称")
    user_name: Optional[str] = Field(None, description="用户名称")


# ==================== Statistics Schemas ====================

class ConfigurationStats(BaseModel):
    """配置统计信息"""
    total_configurations: int = Field(0, description="总配置数")
    enabled_configurations: int = Field(0, description="启用的配置数")
    disabled_configurations: int = Field(0, description="禁用的配置数")
    configurations_by_tool: List[dict] = Field(default_factory=list, description="按工具统计")
    recent_changes: int = Field(0, description="最近变更数量")
    total_history_records: int = Field(0, description="总历史记录数")
