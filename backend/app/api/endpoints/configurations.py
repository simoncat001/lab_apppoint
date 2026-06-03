"""
Configuration API endpoints
工具配置管理 API 端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.core.tool_permissions import require_tool_manager
from app.api.project_context import (
    CurrentProjectContext,
    get_configuration_history_in_current_project,
    get_configuration_in_current_project,
    get_configuration_option_in_current_project,
    get_current_project_context,
    get_reservation_in_current_project,
    get_tool_in_current_project,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.configuration import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationResponse,
    ConfigurationDetail,
    ConfigurationChangeSetting,
    ConfigurationStats,
    ConfigurationOptionCreate,
    ConfigurationOptionUpdate,
    ConfigurationOptionResponse,
    ConfigurationOptionDetail,
    ConfigurationHistoryCreate,
    ConfigurationHistoryResponse,
    ConfigurationHistoryDetail,
)
from app.services.configuration_service import (
    ConfigurationService,
    ConfigurationOptionService,
    ConfigurationHistoryService,
)

router = APIRouter()


def _user_display_name(user: User | None) -> str | None:
    if user is None:
        return None
    first_name = (user.first_name or "").strip()
    last_name = (user.last_name or "").strip()
    return f"{last_name}{first_name}".strip() or user.username


async def get_current_staff_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Staff guard using the real JWT-based auth dependency."""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can access this endpoint",
        )
    return current_user


# ==================== Configuration Endpoints ====================

@router.get("/", response_model=List[ConfigurationResponse])
async def list_configurations(
    response: Response,
    tool_id: Optional[int] = Query(None, description="工具ID筛选"),
    enabled: Optional[bool] = Query(None, description="是否启用筛选"),
    exclude_from_agenda: Optional[bool] = Query(None, description="是否从议程中排除"),
    maintainer_id: Optional[int] = Query(None, description="维护人员ID筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    获取配置列表

    支持按工具、启用状态、维护人员等条件过滤
    """
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)
    configurations = await ConfigurationService.get_configurations(
        db=db,
        tool_id=tool_id,
        project_id=project_ctx.project_id,
        enabled=enabled,
        exclude_from_agenda=exclude_from_agenda,
        maintainer_id=maintainer_id,
        skip=skip,
        limit=limit
    )
    total = await ConfigurationService.count_configurations(
        db=db,
        tool_id=tool_id,
        project_id=project_ctx.project_id,
        enabled=enabled,
        exclude_from_agenda=exclude_from_agenda,
        maintainer_id=maintainer_id,
    )
    response.headers["X-Total-Count"] = str(total)
    return configurations


@router.post("/", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    configuration: ConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    创建配置
    
    需要管理员权限
    """
    await get_tool_in_current_project(db, configuration.tool_id, project_ctx)
    require_tool_manager(current_user, configuration.tool_id)
    return await ConfigurationService.create_configuration(db=db, configuration=configuration)


@router.get("/tool/{tool_id}/list", response_model=List[ConfigurationResponse])
async def get_tool_configurations(
    tool_id: int,
    enabled_only: bool = Query(True, description="仅返回启用的配置"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    获取工具的所有配置
    
    按显示顺序排列
    """
    await get_tool_in_current_project(db, tool_id, project_ctx)
    configurations = await ConfigurationService.get_configurations_by_tool(
        db=db,
        tool_id=tool_id,
        enabled_only=enabled_only
    )
    return configurations


@router.get("/stats", response_model=ConfigurationStats)
async def get_configuration_stats(
    tool_id: Optional[int] = Query(None, description="工具ID筛选"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    获取配置统计信息
    
    需要管理员权限
    """
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)
        require_tool_manager(current_user, tool_id)
    stats = await ConfigurationService.get_configuration_stats(
        db=db,
        tool_id=tool_id,
        days=days,
        project_id=project_ctx.project_id,
    )
    return ConfigurationStats(**stats)


@router.get("/{configuration_id}", response_model=ConfigurationDetail)
async def get_configuration(
    configuration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取配置详情"""
    existing = await get_configuration_in_current_project(db, configuration_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    configuration = await ConfigurationService.get_configuration(db=db, configuration_id=configuration_id)
    if not configuration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    
    # 构建详情响应
    detail = ConfigurationDetail(
        **configuration.__dict__,
        current_settings_list=configuration.current_settings_list,
        available_settings_list=configuration.available_settings_list,
        calendar_colors_list=configuration.calendar_colors_list,
        configurable_item_count=configuration.configurable_item_count,
        maintainer_ids=[m.id for m in configuration.maintainers],
        history_count=len(configuration.history)
    )
    return detail


@router.put("/{configuration_id}", response_model=ConfigurationResponse)
async def update_configuration(
    configuration_id: int,
    configuration: ConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    更新配置
    
    需要管理员权限
    """
    existing = await get_configuration_in_current_project(db, configuration_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    updated = await ConfigurationService.update_configuration(
        db=db,
        configuration_id=configuration_id,
        configuration=configuration
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return updated


@router.delete("/{configuration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    configuration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    删除配置
    
    需要管理员权限
    """
    existing = await get_configuration_in_current_project(db, configuration_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    deleted = await ConfigurationService.delete_configuration(db=db, configuration_id=configuration_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )


@router.post("/{configuration_id}/change-setting", response_model=ConfigurationResponse)
async def change_configuration_setting(
    configuration_id: int,
    change: ConfigurationChangeSetting,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    修改配置设置
    
    需要是配置维护人员
    """
    await get_configuration_in_current_project(db, configuration_id, project_ctx)
    # 检查用户是否为维护人员
    is_maintainer = await ConfigurationService.user_is_maintainer(
        db=db,
        configuration_id=configuration_id,
        user_id=current_user.id
    )
    
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to change this configuration"
        )
    
    try:
        updated = await ConfigurationService.change_configuration_setting(
            db=db,
            configuration_id=configuration_id,
            user_id=current_user.id,
            change=change
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    return updated





# ==================== ConfigurationOption Endpoints ====================

@router.get("/configuration-options", response_model=List[ConfigurationOptionResponse])
async def list_configuration_options(
    reservation_id: Optional[int] = Query(None, description="预约ID筛选"),
    configuration_id: Optional[int] = Query(None, description="配置ID筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    获取配置选项列表
    
    支持按预约、配置等条件过滤
    """
    if reservation_id is not None:
        await get_reservation_in_current_project(db, reservation_id, project_ctx)
    if configuration_id is not None:
        await get_configuration_in_current_project(db, configuration_id, project_ctx)
    options = await ConfigurationOptionService.get_configuration_options(
        db=db,
        reservation_id=reservation_id,
        configuration_id=configuration_id,
        project_id=project_ctx.project_id,
        skip=skip,
        limit=limit
    )
    return options


@router.post("/configuration-options", response_model=ConfigurationOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration_option(
    option: ConfigurationOptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建配置选项"""
    await get_reservation_in_current_project(db, option.reservation_id, project_ctx)
    if option.configuration_id is not None:
        await get_configuration_in_current_project(db, option.configuration_id, project_ctx)
    return await ConfigurationOptionService.create_configuration_option(db=db, option=option)


@router.get("/configuration-options/{option_id}", response_model=ConfigurationOptionDetail)
async def get_configuration_option(
    option_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取配置选项详情"""
    await get_configuration_option_in_current_project(db, option_id, project_ctx)
    option = await ConfigurationOptionService.get_configuration_option(db=db, option_id=option_id)
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration option not found")
    
    # 构建详情响应
    detail = ConfigurationOptionDetail(
        **option.__dict__,
        available_settings_list=option.available_settings_list,
        calendar_colors_list=option.calendar_colors_list,
        color=option.get_color()
    )
    return detail


@router.put("/configuration-options/{option_id}", response_model=ConfigurationOptionResponse)
async def update_configuration_option(
    option_id: int,
    option: ConfigurationOptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新配置选项"""
    await get_configuration_option_in_current_project(db, option_id, project_ctx)
    updated = await ConfigurationOptionService.update_configuration_option(
        db=db,
        option_id=option_id,
        option=option
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration option not found"
        )
    return updated


@router.delete("/configuration-options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_option(
    option_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除配置选项"""
    await get_configuration_option_in_current_project(db, option_id, project_ctx)
    deleted = await ConfigurationOptionService.delete_configuration_option(db=db, option_id=option_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration option not found"
        )


# ==================== ConfigurationHistory Endpoints ====================

@router.get("/configuration-history", response_model=List[ConfigurationHistoryDetail])
async def list_configuration_history(
    configuration_id: Optional[int] = Query(None, description="配置ID筛选"),
    tool_id: Optional[int] = Query(None, description="工具ID筛选"),
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    获取配置历史列表
    
    支持按配置、工具、用户、时间等条件过滤
    """
    if configuration_id is not None:
        await get_configuration_in_current_project(db, configuration_id, project_ctx)
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)
    history = await ConfigurationHistoryService.get_configuration_history(
        db=db,
        configuration_id=configuration_id,
        tool_id=tool_id,
        project_id=project_ctx.project_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    
    # 构建详情列表
    result = []
    for h in history:
        detail = ConfigurationHistoryDetail(
            **h.__dict__,
            configuration_name=h.configuration.name if h.configuration else None,
            user_name=_user_display_name(h.user)
        )
        result.append(detail)
    
    return result


@router.get("/configuration-history/{history_id}", response_model=ConfigurationHistoryDetail)
async def get_configuration_history_detail(
    history_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取配置历史详情"""
    await get_configuration_history_in_current_project(db, history_id, project_ctx)
    history = await ConfigurationHistoryService.get_configuration_history_detail(db=db, history_id=history_id)
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration history not found")
    
    detail = ConfigurationHistoryDetail(
        **history.__dict__,
        configuration_name=history.configuration.name if history.configuration else None,
        user_name=_user_display_name(history.user)
    )
    return detail


@router.post("/configuration-history", response_model=ConfigurationHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration_history(
    history: ConfigurationHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    创建配置历史记录
    
    需要管理员权限（通常由系统自动创建）
    """
    await get_configuration_in_current_project(db, history.configuration_id, project_ctx)
    return await ConfigurationHistoryService.create_configuration_history(
        db=db,
        user_id=current_user.id,
        history=history
    )
