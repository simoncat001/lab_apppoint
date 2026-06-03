"""
Tool API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.project_context import (
    CurrentProjectContext,
    get_current_project_context,
    get_tool_in_current_project,
)
from app.schemas.tool import (
    Tool,
    ToolAdmin,
    ToolAdminUpdate,
    ToolImage as ToolImageSchema,
    ToolCreate,
    ToolUpdate,
    ToolEnable,
    ToolDisable,
    ToolProjectSuggestRequest,
    ToolProjectSuggestResponse,
    ToolCategory,
    ToolCategoryCreate,
    ToolTag,
    ToolTagCreate,
    ToolUserAccessGrant,
    ToolUserAccessInfo,
)
from app.models.tool_user_access import ToolUserAccess
from app.models.tool_image import ToolImage as ToolImageModel
from app.schemas.tool_rate import ToolRateCreate, ToolRateResponse
from app.models.tool_rate import ToolRate
from app.schemas.usage_event import UsageEventResponse
from app.services.project_service import ProjectService
from app.services.security_server_project_service import (
    SecurityServerProjectService,
    SecurityServerProjectServiceError,
)
from app.services.tool_service import ToolService
from app.core.media import remove_tool_image_file, save_image_upload
from app.core.tool_permissions import is_global_tool_admin, require_tool_manager
from sqlalchemy import select, and_, func, or_
from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()


def _parse_tag_ids(value: str | None) -> List[int] | None:
    if not value:
        return None
    parts = [item.strip() for item in value.split(",") if item.strip()]
    if not parts:
        return None
    return [int(item) for item in parts]


def _sorted_tool_images(tool) -> list[ToolImageModel]:
    return sorted(
        list(getattr(tool, "images", []) or []),
        key=lambda image: (int(getattr(image, "sort_order", 0) or 0), int(getattr(image, "id", 0) or 0)),
    )


def _sync_tool_cover_image(tool) -> None:
    images = _sorted_tool_images(tool)
    tool.image = images[0].path if images else ""


async def _get_tool_admin_users(db: AsyncSession, tool_id: int) -> list[User]:
    result = await db.execute(select(User).where(or_(User.is_staff == True, User.is_superuser == True)))
    users = list(result.scalars().all())
    return [user for user in users if int(tool_id) in set(user.managed_tool_ids_list or [])]


@router.get("/", response_model=List[Tool])
async def get_tools(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    visible_only: bool = False,
    visible: bool | None = None,
    operational_only: bool = False,
    name: str | None = None,
    category_id: int | None = None,
    tag_ids: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取工具列表"""
    service = ToolService(db)
    parsed_tag_ids = _parse_tag_ids(tag_ids)
    if ToolService._is_external_user(current_user):
        visible = True
    tools = await service.get_tools(
        skip=skip,
        limit=limit,
        visible_only=visible_only,
        visible=visible,
        operational_only=operational_only,
        name=name,
        category_id=category_id,
        tag_ids=parsed_tag_ids,
        project_id=project_ctx.project_id,
        current_user=current_user,
    )
    total = await service.count_tools(
        visible_only=visible_only,
        visible=visible,
        operational_only=operational_only,
        name=name,
        category_id=category_id,
        tag_ids=parsed_tag_ids,
        project_id=project_ctx.project_id,
        current_user=current_user,
    )
    response.headers["X-Total-Count"] = str(total)
    return tools


@router.get("/categories", response_model=List[ToolCategory])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ToolService(db)
    return await service.get_categories()


@router.post("/categories", response_model=ToolCategory)
async def create_category(
    payload: ToolCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    service = ToolService(db)
    return await service.create_category(payload.name)


@router.put("/categories/{category_id}", response_model=ToolCategory)
async def update_category(
    category_id: int,
    payload: ToolCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    service = ToolService(db)
    category = await service.update_category(category_id, payload.name)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/categories/{category_id}", response_model=bool)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    service = ToolService(db)
    success = await service.delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return True


@router.get("/tags", response_model=List[ToolTag])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ToolService(db)
    return await service.get_tags()


@router.post("/tags", response_model=ToolTag)
async def create_tag(
    payload: ToolTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage tags")
    service = ToolService(db)
    return await service.create_tag(payload.name)


@router.put("/tags/{tag_id}", response_model=ToolTag)
async def update_tag(
    tag_id: int,
    payload: ToolTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage tags")
    service = ToolService(db)
    tag = await service.update_tag(tag_id, payload.name)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.delete("/tags/{tag_id}", response_model=bool)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage tags")
    service = ToolService(db)
    success = await service.delete_tag(tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return True


@router.post("/project-suggestion", response_model=ToolProjectSuggestResponse)
async def suggest_tool_project(
    payload: ToolProjectSuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据仪器信息智能建议所属项目"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can use tool project suggestion",
        )

    if SecurityServerProjectService.is_enabled():
        project_service = ProjectService(db)
        try:
            await project_service.sync_projects_from_security_server()
        except SecurityServerProjectServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    service = ToolService(db)
    return await service.suggest_project_for_tool(payload)


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取单个工具"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    service = ToolService(db)
    tool = await service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    if ToolService._is_external_user(current_user):
        if not tool.visible:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
        if not await service.check_external_user_tool_access(tool_id, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this tool")
    return tool


@router.post("/{tool_id}/rates", response_model=ToolRateResponse)
async def create_tool_rate(
    tool_id: int,
    rate_in: ToolRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建工具费率（管理员）"""
    if rate_in.tool_id != tool_id:
        raise HTTPException(status_code=400, detail="Tool ID mismatch")
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)

    rate = ToolRate(**rate_in.model_dump())
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return rate

@router.get("/{tool_id}/rates", response_model=List[ToolRateResponse])
async def get_tool_rates(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取工具费率"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    # Anyone can see rates? Usually yes.
    result = await db.execute(select(ToolRate).where(ToolRate.tool_id == tool_id))
    return result.scalars().all()

@router.delete("/{tool_id}/rates/{rate_id}", status_code=204)
async def delete_tool_rate(
    tool_id: int,
    rate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除工具费率（管理员）"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
         
    result = await db.execute(select(ToolRate).where(and_(ToolRate.id == rate_id, ToolRate.tool_id == tool_id)))
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
        
    await db.delete(rate)
    await db.commit()


@router.post("/{tool_id}/image", response_model=Tool)
async def upload_tool_image(
    tool_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """上传仪器图片（仅管理员）

    新版存储路径：media/tools/{tool_id}/{uuid}.{ext}
    DB tool.image 继续保留为封面图，tool_image 表存放完整图片列表。
    """
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)

    service = ToolService(db)
    tool = await service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    filename, url = await save_image_upload("tools", tool_id, file)
    stored_path = f"tools/{tool_id}/{filename}"
    max_sort_result = await db.execute(
        select(func.max(ToolImageModel.sort_order)).where(ToolImageModel.tool_id == tool_id)
    )
    next_sort_order = int(max_sort_result.scalar() or -1) + 1
    db.add(
        ToolImageModel(
            tool_id=tool_id,
            path=stored_path,
            sort_order=next_sort_order,
        )
    )
    if not tool.image:
        tool.image = stored_path
    await db.commit()
    return await service.get_tool(tool_id)


@router.delete("/{tool_id}/image", response_model=Tool)
async def delete_tool_image(
    tool_id: int,
    image_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除仪器图片（仅管理员）。

    - 传 `image_id`：删除指定图片
    - 不传 `image_id`：兼容旧版行为，删除当前封面图
    """
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    service = ToolService(db)
    tool = await service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    target_image = None
    if image_id is not None:
        target_image = next((image for image in _sorted_tool_images(tool) if image.id == image_id), None)
        if target_image is None:
            raise HTTPException(status_code=404, detail="Image not found")
    elif tool.images:
        cover_path = tool.image or _sorted_tool_images(tool)[0].path
        target_image = next((image for image in _sorted_tool_images(tool) if image.path == cover_path), None)

    if target_image is not None:
        remove_tool_image_file(target_image.path)
        remaining_images = [image for image in _sorted_tool_images(tool) if image.id != target_image.id]
        await db.delete(target_image)
        tool.image = remaining_images[0].path if remaining_images else ""
        await db.commit()
    elif tool.image:
        remove_tool_image_file(tool.image)
        tool.image = ""
        await db.commit()

    return await service.get_tool(tool_id)


# ==================== 设备级用户权限管理 ====================


@router.get("/{tool_id}/access", response_model=List[ToolUserAccessInfo])
async def list_tool_access(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """查询仪器已授权用户列表（仅管理员）"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    result = await db.execute(
        select(ToolUserAccess).where(ToolUserAccess.tool_id == tool_id)
    )
    records = result.scalars().all()
    # 补充用户信息
    infos = []
    for rec in records:
        user = (await db.execute(select(User).where(User.id == rec.user_id))).scalar_one_or_none()
        infos.append(ToolUserAccessInfo(
            id=rec.id,
            tool_id=rec.tool_id,
            user_id=rec.user_id,
            username=user.username if user else "",
            first_name=user.first_name if user else "",
            last_name=user.last_name if user else "",
            granted_by=rec.granted_by,
            granted_at=rec.granted_at,
        ))
    return infos


@router.post("/{tool_id}/access", response_model=ToolUserAccessInfo, status_code=status.HTTP_201_CREATED)
async def grant_tool_access(
    tool_id: int,
    payload: ToolUserAccessGrant,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """授权用户使用仪器（仅管理员）"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)

    # 检查用户是否存在
    target_user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 检查是否已授权
    existing = (await db.execute(
        select(ToolUserAccess).where(
            and_(ToolUserAccess.tool_id == tool_id, ToolUserAccess.user_id == payload.user_id)
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户已拥有该仪器的使用权限")

    record = ToolUserAccess(tool_id=tool_id, user_id=payload.user_id, granted_by=current_user.id)
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return ToolUserAccessInfo(
        id=record.id,
        tool_id=record.tool_id,
        user_id=record.user_id,
        username=target_user.username,
        first_name=target_user.first_name,
        last_name=target_user.last_name,
        granted_by=record.granted_by,
        granted_at=record.granted_at,
    )


@router.delete("/{tool_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_tool_access(
    tool_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """撤销用户仪器使用权限（仅管理员）"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    record = (await db.execute(
        select(ToolUserAccess).where(
            and_(ToolUserAccess.tool_id == tool_id, ToolUserAccess.user_id == user_id)
        )
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Access record not found")
    await db.delete(record)
    await db.commit()


@router.get("/{tool_id}/admins", response_model=List[ToolAdmin])
async def list_tool_admins(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """查询单台仪器管理员。"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    return await _get_tool_admin_users(db, tool_id)


@router.put("/{tool_id}/admins", response_model=List[ToolAdmin])
async def update_tool_admins(
    tool_id: int,
    payload: ToolAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """设置单台仪器管理员。管理员必须是 staff 或 superuser 用户。"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)

    selected_ids = {int(user_id) for user_id in payload.user_ids}
    if selected_ids:
        selected_result = await db.execute(select(User).where(User.id.in_(selected_ids)))
        selected_users = list(selected_result.scalars().all())
        found_ids = {int(user.id) for user in selected_users}
        if found_ids != selected_ids:
            raise HTTPException(status_code=404, detail="Some users were not found")
        if any(not (user.is_staff or user.is_superuser) for user in selected_users):
            raise HTTPException(status_code=400, detail="Only staff or superuser users can be tool administrators")

    result = await db.execute(select(User).where(or_(User.is_staff == True, User.is_superuser == True)))
    staff_users = list(result.scalars().all())
    for user in staff_users:
        managed_ids = set(user.managed_tool_ids_list or [])
        if int(user.id) in selected_ids:
            managed_ids.add(int(tool_id))
        else:
            managed_ids.discard(int(tool_id))
        user.managed_tool_ids_list = sorted(managed_ids)

    await db.commit()
    return await _get_tool_admin_users(db, tool_id)


@router.post("/", response_model=Tool, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_in: ToolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建新工具"""
    if not is_global_tool_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global staff can create tools",
        )
    service = ToolService(db)
    
    # 如果未指定负责人，默认为当前用户
    if tool_in.primary_owner_id is None:
        tool_in.primary_owner_id = current_user.id

    if tool_in.project_id is None:
        tool_in.project_id = project_ctx.project_id
    elif int(tool_in.project_id) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New tools can only be created under the current project",
        )
    
    try:
        tool = await service.create_tool(tool_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return tool


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(
    tool_id: int,
    tool_in: ToolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新工具"""
    service = ToolService(db)
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    if tool_in.project_id is not None and int(tool_in.project_id) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool transfer across projects is not allowed in current project workspace",
        )
    try:
        tool = await service.update_tool(tool_id, tool_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    return tool


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除工具"""
    service = ToolService(db)
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    success = await service.delete_tool(tool_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    return None


@router.get("/{tool_id}/status", response_model=bool)
async def get_tool_status(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取工具状态（是否正在使用）"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    service = ToolService(db)
    usage = await service.get_current_usage(tool_id)
    return usage is not None


@router.post("/{tool_id}/enable", response_model=UsageEventResponse)
async def enable_tool(
    tool_id: int,
    enable_data: ToolEnable,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """启用工具"""
    service = ToolService(db)
    tool = await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)

    if enable_data.project_id is not None and int(enable_data.project_id) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enable request project_id must match current project",
        )
    if getattr(tool, "project_id", None) is not None and int(tool.project_id) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool does not belong to the current project",
        )
    
    # 如果未指定操作员，默认为当前用户
    operator_id = enable_data.operator_id or current_user.id
    
    try:
        usage_event = await service.enable_tool(tool_id, enable_data, operator_id)
        return usage_event
    except ValueError as e:
        await db.rollback()
        response_status = (
            status.HTTP_409_CONFLICT
            if "already in use" in str(e) or "currently in use" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=response_status,
            detail=str(e)
        )


@router.post("/{tool_id}/disable", response_model=UsageEventResponse)
async def disable_tool(
    tool_id: int,
    disable_data: ToolDisable,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """禁用工具"""
    service = ToolService(db)
    await get_tool_in_current_project(db, tool_id, project_ctx)
    require_tool_manager(current_user, tool_id)
    try:
        usage_event = await service.disable_tool(tool_id, disable_data)
        return usage_event
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
