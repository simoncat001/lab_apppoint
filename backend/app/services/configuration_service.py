"""
Configuration Service Layer
工具配置管理服务层
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_, or_, select

from app.models.configuration import Configuration, ConfigurationOption, ConfigurationHistory
from app.models.tool import Tool
from app.models.user import User
from app.models.reservation import Reservation
from app.schemas.configuration import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationChangeSetting,
    ConfigurationOptionCreate,
    ConfigurationOptionUpdate,
    ConfigurationHistoryCreate,
)


class ConfigurationService:
    """配置服务类"""
    
    @staticmethod
    async def get_configurations(
        db: AsyncSession,
        tool_id: Optional[int] = None,
        project_id: Optional[int] = None,
        enabled: Optional[bool] = None,
        exclude_from_agenda: Optional[bool] = None,
        maintainer_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Configuration]:
        """获取配置列表（支持多维度过滤）"""
        query = select(Configuration)
        
        if tool_id is not None:
            query = query.where(Configuration.tool_id == tool_id)
        if project_id is not None:
            query = query.join(Tool, Configuration.tool_id == Tool.id).where(Tool.project_id == project_id)
        
        if enabled is not None:
            query = query.where(Configuration.enabled == enabled)
        
        if exclude_from_agenda is not None:
            query = query.where(Configuration.exclude_from_configuration_agenda == exclude_from_agenda)
        
        if maintainer_id is not None:
            query = query.join(Configuration.maintainers).where(User.id == maintainer_id)
        
        result = await db.execute(query.order_by(Configuration.display_order).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def count_configurations(
        db: AsyncSession,
        tool_id: Optional[int] = None,
        project_id: Optional[int] = None,
        enabled: Optional[bool] = None,
        exclude_from_agenda: Optional[bool] = None,
        maintainer_id: Optional[int] = None,
    ) -> int:
        query = select(func.count(func.distinct(Configuration.id))).select_from(Configuration)
        if project_id is not None:
            query = query.join(Tool, Configuration.tool_id == Tool.id).where(Tool.project_id == project_id)
        if tool_id is not None:
            query = query.where(Configuration.tool_id == tool_id)
        if enabled is not None:
            query = query.where(Configuration.enabled == enabled)
        if exclude_from_agenda is not None:
            query = query.where(Configuration.exclude_from_configuration_agenda == exclude_from_agenda)
        if maintainer_id is not None:
            query = query.join(Configuration.maintainers).where(User.id == maintainer_id)
        result = await db.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def get_configuration(db: AsyncSession, configuration_id: int) -> Optional[Configuration]:
        """获取单个配置详情"""
        query = select(Configuration).options(
            joinedload(Configuration.maintainers),
            joinedload(Configuration.history)
        ).where(Configuration.id == configuration_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_configuration(
        db: AsyncSession, 
        configuration: ConfigurationCreate
    ) -> Configuration:
        """创建配置"""
        # 创建配置对象
        db_configuration = Configuration(
            name=configuration.name,
            tool_id=configuration.tool_id,
            configurable_item_name=configuration.configurable_item_name,
            advance_notice_limit=configuration.advance_notice_limit,
            display_order=configuration.display_order,
            prompt=configuration.prompt,
            current_settings=configuration.current_settings,
            available_settings=configuration.available_settings,
            calendar_colors=configuration.calendar_colors,
            absence_string=configuration.absence_string,
            qualified_users_are_maintainers=configuration.qualified_users_are_maintainers,
            exclude_from_configuration_agenda=configuration.exclude_from_configuration_agenda,
            enabled=configuration.enabled,
        )
        
        # 添加维护人员
        if configuration.maintainer_ids:
            result = await db.execute(select(User).where(User.id.in_(configuration.maintainer_ids)))
            maintainers = result.scalars().all()
            db_configuration.maintainers = list(maintainers)
        
        db.add(db_configuration)
        await db.commit()
        await db.refresh(db_configuration)
        return db_configuration
    
    @staticmethod
    async def update_configuration(
        db: AsyncSession,
        configuration_id: int,
        configuration: ConfigurationUpdate
    ) -> Optional[Configuration]:
        """更新配置"""
        result = await db.execute(select(Configuration).where(Configuration.id == configuration_id))
        db_configuration = result.scalars().first()
        
        if not db_configuration:
            return None
        
        # 更新字段
        update_data = configuration.model_dump(exclude_unset=True, exclude={"maintainer_ids"})
        for field, value in update_data.items():
            setattr(db_configuration, field, value)
        
        # 更新维护人员
        if configuration.maintainer_ids is not None:
            result = await db.execute(select(User).where(User.id.in_(configuration.maintainer_ids)))
            maintainers = result.scalars().all()
            db_configuration.maintainers = list(maintainers)
        
        await db.commit()
        await db.refresh(db_configuration)
        return db_configuration
    
    @staticmethod
    async def delete_configuration(db: AsyncSession, configuration_id: int) -> bool:
        """删除配置"""
        result = await db.execute(select(Configuration).where(Configuration.id == configuration_id))
        db_configuration = result.scalars().first()
        
        if not db_configuration:
            return False
        
        await db.delete(db_configuration)
        await db.commit()
        return True
    
    @staticmethod
    async def change_configuration_setting(
        db: AsyncSession,
        configuration_id: int,
        user_id: int,
        change: ConfigurationChangeSetting
    ) -> Optional[Configuration]:
        """修改配置设置"""
        result = await db.execute(select(Configuration).where(Configuration.id == configuration_id))
        db_configuration = result.scalars().first()
        
        if not db_configuration:
            return None
        
        # 获取可选设置列表
        available_settings = db_configuration.available_settings_list
        if change.choice < 0 or change.choice >= len(available_settings):
            raise ValueError("Invalid choice index")
        
        # 获取当前设置列表
        current_settings = db_configuration.current_settings_list
        if change.slot < 0 or change.slot >= len(current_settings):
            raise ValueError("Invalid slot index")
        
        # 修改设置
        current_settings[change.slot] = available_settings[change.choice]
        db_configuration.current_settings = ", ".join(current_settings)
        
        # 创建历史记录
        item_name = db_configuration.configurable_item_name or db_configuration.name
        if len(current_settings) > 1:
            item_name += f" #{change.slot + 1}"
        
        history = ConfigurationHistory(
            configuration_id=configuration_id,
            user_id=user_id,
            modification_time=datetime.now().isoformat(),
            item_name=item_name,
            slot=change.slot,
            setting=current_settings[change.slot]
        )
        
        db.add(history)
        await db.commit()
        await db.refresh(db_configuration)
        return db_configuration
    
    @staticmethod
    async def get_configurations_by_tool(
        db: AsyncSession,
        tool_id: int,
        enabled_only: bool = True
    ) -> List[Configuration]:
        """获取工具的所有配置（按显示顺序排列）"""
        query = select(Configuration).where(Configuration.tool_id == tool_id)
        
        if enabled_only:
            query = query.where(Configuration.enabled == True)
        
        result = await db.execute(query.order_by(Configuration.display_order))
        return result.scalars().all()
    
    @staticmethod
    async def user_is_maintainer(
        db: AsyncSession,
        configuration_id: int,
        user_id: int
    ) -> bool:
        """检查用户是否为配置维护人员"""
        query = select(Configuration).options(
            joinedload(Configuration.maintainers),
            joinedload(Configuration.tool)
        ).where(Configuration.id == configuration_id)
        result = await db.execute(query)
        configuration = result.scalars().first()
        
        if not configuration:
            return False
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            return False
        
        # 检查是否为管理员
        if user.is_staff:
            return True
        
        # 检查是否在维护人员列表中
        if user in configuration.maintainers:
            return True
        
        # 检查是否合格用户可以维护
        # TODO: 需要实现工具合格用户检查
        # if configuration.qualified_users_are_maintainers:
        #     if user in configuration.tool.qualified_users:
        #         return True
        
        return False
    
    @staticmethod
    async def get_configuration_stats(
        db: AsyncSession,
        tool_id: Optional[int] = None,
        days: int = 30,
        project_id: Optional[int] = None,
    ) -> dict:
        """获取配置统计信息"""
        query = select(func.count()).select_from(Configuration)
        if project_id is not None:
            query = query.join(Tool, Configuration.tool_id == Tool.id).where(Tool.project_id == project_id)
        
        if tool_id:
            query = query.where(Configuration.tool_id == tool_id)
        
        # 总配置数
        total = (await db.execute(query)).scalar() or 0
        
        # 启用/禁用统计
        enabled_query = query.where(Configuration.enabled == True)
        enabled_count = (await db.execute(enabled_query)).scalar() or 0
        disabled_count = total - enabled_count
        
        # 按工具统计
        tool_stats_query = select(
            Tool.id,
            Tool.name,
            func.count(Configuration.id).label('count')
        ).join(Configuration).group_by(Tool.id, Tool.name)
        if project_id is not None:
            tool_stats_query = tool_stats_query.where(Tool.project_id == project_id)
        if tool_id is not None:
            tool_stats_query = tool_stats_query.where(Tool.id == tool_id)
        
        tool_stats = (await db.execute(tool_stats_query)).all()
        
        configurations_by_tool = [
            {"tool_id": t_id, "tool_name": t_name, "count": count}
            for t_id, t_name, count in tool_stats
        ]
        
        # 最近变更统计
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_changes_query = select(func.count()).select_from(ConfigurationHistory).where(
            ConfigurationHistory.modification_time >= cutoff_date
        )
        if project_id is not None:
            recent_changes_query = (
                recent_changes_query
                .join(Configuration, ConfigurationHistory.configuration_id == Configuration.id)
                .join(Tool, Configuration.tool_id == Tool.id)
                .where(Tool.project_id == project_id)
            )
        if tool_id is not None:
            if project_id is None:
                recent_changes_query = recent_changes_query.join(
                    Configuration, ConfigurationHistory.configuration_id == Configuration.id
                )
            recent_changes_query = recent_changes_query.where(Configuration.tool_id == tool_id)
        recent_changes = (await db.execute(recent_changes_query)).scalar() or 0
        
        # 总历史记录数
        total_history_query = select(func.count()).select_from(ConfigurationHistory)
        if project_id is not None:
            total_history_query = (
                total_history_query
                .join(Configuration, ConfigurationHistory.configuration_id == Configuration.id)
                .join(Tool, Configuration.tool_id == Tool.id)
                .where(Tool.project_id == project_id)
            )
        if tool_id is not None:
            if project_id is None:
                total_history_query = total_history_query.join(
                    Configuration, ConfigurationHistory.configuration_id == Configuration.id
                )
            total_history_query = total_history_query.where(Configuration.tool_id == tool_id)
        total_history = (await db.execute(total_history_query)).scalar() or 0
        
        return {
            "total_configurations": total,
            "enabled_configurations": enabled_count,
            "disabled_configurations": disabled_count,
            "configurations_by_tool": configurations_by_tool,
            "recent_changes": recent_changes,
            "total_history_records": total_history,
        }


class ConfigurationOptionService:
    """配置选项服务类"""
    
    @staticmethod
    async def get_configuration_options(
        db: AsyncSession,
        reservation_id: Optional[int] = None,
        configuration_id: Optional[int] = None,
        project_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConfigurationOption]:
        """获取配置选项列表"""
        query = select(ConfigurationOption)
        if project_id is not None:
            query = query.join(Reservation, ConfigurationOption.reservation_id == Reservation.id).where(
                Reservation.project_id == project_id
            )
        
        if reservation_id is not None:
            query = query.where(ConfigurationOption.reservation_id == reservation_id)
        
        if configuration_id is not None:
            query = query.where(ConfigurationOption.configuration_id == configuration_id)
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()
    
    @staticmethod
    async def get_configuration_option(
        db: AsyncSession,
        option_id: int
    ) -> Optional[ConfigurationOption]:
        """获取单个配置选项详情"""
        query = select(ConfigurationOption).options(
            joinedload(ConfigurationOption.configuration),
            joinedload(ConfigurationOption.reservation)
        ).where(ConfigurationOption.id == option_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_configuration_option(
        db: AsyncSession,
        option: ConfigurationOptionCreate
    ) -> ConfigurationOption:
        """创建配置选项"""
        db_option = ConfigurationOption(**option.model_dump())
        db.add(db_option)
        await db.commit()
        await db.refresh(db_option)
        return db_option
    
    @staticmethod
    async def update_configuration_option(
        db: AsyncSession,
        option_id: int,
        option: ConfigurationOptionUpdate
    ) -> Optional[ConfigurationOption]:
        """更新配置选项"""
        result = await db.execute(select(ConfigurationOption).where(ConfigurationOption.id == option_id))
        db_option = result.scalars().first()
        
        if not db_option:
            return None
        
        update_data = option.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_option, field, value)
        
        await db.commit()
        await db.refresh(db_option)
        return db_option
    
    @staticmethod
    async def delete_configuration_option(db: AsyncSession, option_id: int) -> bool:
        """删除配置选项"""
        result = await db.execute(select(ConfigurationOption).where(ConfigurationOption.id == option_id))
        db_option = result.scalars().first()
        
        if not db_option:
            return False
        
        await db.delete(db_option)
        await db.commit()
        return True


class ConfigurationHistoryService:
    """配置历史服务类"""
    
    @staticmethod
    async def get_configuration_history(
        db: AsyncSession,
        configuration_id: Optional[int] = None,
        tool_id: Optional[int] = None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConfigurationHistory]:
        """获取配置历史列表（支持多维度过滤）"""
        query = select(ConfigurationHistory).options(
            joinedload(ConfigurationHistory.configuration),
            joinedload(ConfigurationHistory.user)
        )
        
        if configuration_id is not None:
            query = query.where(ConfigurationHistory.configuration_id == configuration_id)
        
        if tool_id is not None:
            query = query.join(Configuration).where(Configuration.tool_id == tool_id)
        if project_id is not None:
            # Reuse joins if already joined to Configuration above.
            if tool_id is not None:
                query = query.join(Tool, Configuration.tool_id == Tool.id)
            else:
                query = query.join(Configuration).join(Tool, Configuration.tool_id == Tool.id)
            query = query.where(Tool.project_id == project_id)
        
        if user_id is not None:
            query = query.where(ConfigurationHistory.user_id == user_id)
        
        if start_date:
            query = query.where(ConfigurationHistory.modification_time >= start_date)
        
        if end_date:
            query = query.where(ConfigurationHistory.modification_time <= end_date)
        
        result = await db.execute(query.order_by(ConfigurationHistory.modification_time.desc()).offset(skip).limit(limit))
        return result.scalars().all()
    
    @staticmethod
    async def get_configuration_history_detail(
        db: AsyncSession,
        history_id: int
    ) -> Optional[ConfigurationHistory]:
        """获取单条历史记录详情"""
        query = select(ConfigurationHistory).options(
            joinedload(ConfigurationHistory.configuration),
            joinedload(ConfigurationHistory.user)
        ).where(ConfigurationHistory.id == history_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_configuration_history(
        db: AsyncSession,
        user_id: int,
        history: ConfigurationHistoryCreate
    ) -> ConfigurationHistory:
        """创建配置历史记录"""
        db_history = ConfigurationHistory(
            configuration_id=history.configuration_id,
            user_id=user_id,
            modification_time=datetime.now().isoformat(),
            item_name=history.item_name,
            slot=history.slot,
            setting=history.setting
        )
        
        db.add(db_history)
        await db.commit()
        await db.refresh(db_history)
        return db_history
