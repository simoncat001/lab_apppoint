"""
Tool service layer
"""

import re
import unicodedata
from datetime import datetime
from typing import List, Optional
from sqlalchemy import or_, select, and_, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.tool import Tool
from app.models.tool_image import ToolImage
from app.models.project import Project
from app.models.tool_category import ToolCategory
from app.models.tool_tag import ToolTag
from app.models.tool_tag_link import tool_tag_link
from app.models.tool_user_access import ToolUserAccess
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolEnable,
    ToolDisable,
    ToolProjectSuggestRequest,
    ToolProjectSuggestCandidate,
    ToolProjectSuggestResponse,
)
from app.services.account_service import AccountService
from app.services.usage_event_service import UsageEventService


class ToolService:
    _SUGGEST_STOPWORDS = {
        "项目",
        "平台",
        "实验室",
        "中心",
        "仪器",
        "设备",
        "系统",
        "管理",
        "共享",
        "公共",
        "测试",
        "学院",
        "大学",
        "研究院",
        "研究所",
        "研究",
        "课题组",
        "课题",
        "lab",
        "labs",
        "project",
        "projects",
        "platform",
        "center",
        "centre",
        "system",
        "management",
        "test",
        "testing",
        "instrument",
        "equipment",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _is_tool_name_integrity_error(exc: IntegrityError) -> bool:
        message = str(exc.orig or exc)
        return "uq_tool_project_name" in message or "Duplicate entry" in message
    
    @staticmethod
    def _is_external_user(user: Optional["User"]) -> bool:
        """判断是否为外部用户"""
        if user is None:
            return False
        return (
            getattr(user, "auth_source", "local") == "local"
            and not getattr(user, "is_superuser", False)
            and not getattr(user, "is_staff", False)
        )

    def _apply_tool_filters(
        self,
        query,
        *,
        visible: Optional[bool],
        operational_only: bool,
        name: Optional[str],
        category_id: Optional[int],
        tag_ids: Optional[List[int]],
        project_id: Optional[int],
        current_user: Optional["User"],
    ):
        """共享的过滤条件构造（list 与 count 共用，保持一致性）。"""
        if visible is not None:
            query = query.where(Tool.visible == visible)
        if operational_only:
            query = query.where(Tool.operational == True)
        if name:
            query = query.where(Tool.name.like(f"%{name}%"))
        if project_id:
            query = query.where(Tool.project_id == project_id)
        if category_id:
            query = query.where(Tool.category_id == category_id)
        if tag_ids:
            query = (
                query.join(tool_tag_link, tool_tag_link.c.tool_id == Tool.id)
                .where(tool_tag_link.c.tag_id.in_(tag_ids))
                .group_by(Tool.id)
                .having(func.count(func.distinct(tool_tag_link.c.tag_id)) == len(tag_ids))
            )
        if self._is_external_user(current_user) and current_user is not None:
            accessible_subq = (
                select(ToolUserAccess.tool_id)
                .where(ToolUserAccess.user_id == current_user.id)
            )
            query = query.where(
                or_(
                    Tool.restrict_external_access == False,
                    Tool.id.in_(accessible_subq),
                )
            )
        return query

    async def get_tools(
        self,
        skip: int = 0,
        limit: int = 100,
        visible_only: bool = False,
        operational_only: bool = False,
        name: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        project_id: Optional[int] = None,
        current_user: Optional["User"] = None,
        visible: Optional[bool] = None,
    ) -> List[Tool]:
        """获取工具列表"""
        if visible is None and visible_only:
            visible = True
        query = select(Tool).options(
            selectinload(Tool.category),
            selectinload(Tool.project),
            selectinload(Tool.tags),
            selectinload(Tool.images),
        )
        query = self._apply_tool_filters(
            query,
            visible=visible,
            operational_only=operational_only,
            name=name,
            category_id=category_id,
            tag_ids=tag_ids,
            project_id=project_id,
            current_user=current_user,
        )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_tools(
        self,
        visible_only: bool = False,
        operational_only: bool = False,
        name: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        project_id: Optional[int] = None,
        current_user: Optional["User"] = None,
        visible: Optional[bool] = None,
    ) -> int:
        """统计工具总数（与 get_tools 同样的过滤条件，不分页）。"""
        if visible is None and visible_only:
            visible = True
        if tag_ids:
            base = select(Tool.id).select_from(Tool)
            base = self._apply_tool_filters(
                base,
                visible=visible,
                operational_only=operational_only,
                name=name,
                category_id=category_id,
                tag_ids=tag_ids,
                project_id=project_id,
                current_user=current_user,
            )
            query = select(func.count()).select_from(base.subquery())
        else:
            query = select(func.count(func.distinct(Tool.id))).select_from(Tool)
            query = self._apply_tool_filters(
                query,
                visible=visible,
                operational_only=operational_only,
                name=name,
                category_id=category_id,
                tag_ids=None,
                project_id=project_id,
                current_user=current_user,
            )
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def check_external_user_tool_access(self, tool_id: int, user: "User") -> bool:
        """检查外部用户是否有权限使用指定仪器。内部用户/staff 始终返回 True。"""
        if not self._is_external_user(user):
            return True
        tool = await self.get_tool(tool_id)
        if not tool or not tool.restrict_external_access:
            return True
        result = await self.db.execute(
            select(ToolUserAccess).where(
                and_(ToolUserAccess.tool_id == tool_id, ToolUserAccess.user_id == user.id)
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_tool(self, tool_id: int) -> Optional[Tool]:
        """获取单个工具"""
        result = await self.db.execute(
            select(Tool)
            .options(
                selectinload(Tool.category),
                selectinload(Tool.project),
                selectinload(Tool.tags),
                selectinload(Tool.images),
            )
            .where(Tool.id == tool_id)
        )
        return result.scalar_one_or_none()
    
    async def get_tool_by_name(
        self,
        name: str,
        project_id: Optional[int] = None,
        exclude_tool_id: Optional[int] = None,
    ) -> Optional[Tool]:
        """通过名称获取工具，可按项目范围过滤。"""
        query = (
            select(Tool)
            .options(
                selectinload(Tool.category),
                selectinload(Tool.project),
                selectinload(Tool.tags),
                selectinload(Tool.images),
            )
            .where(Tool.name == name)
        )
        if project_id is None:
            query = query.where(Tool.project_id.is_(None))
        else:
            query = query.where(Tool.project_id == project_id)
        if exclude_tool_id is not None:
            query = query.where(Tool.id != exclude_tool_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def ensure_tool_name_available(
        self,
        name: str,
        project_id: Optional[int],
        exclude_tool_id: Optional[int] = None,
    ) -> None:
        existing_tool = await self.get_tool_by_name(
            name=name,
            project_id=project_id,
            exclude_tool_id=exclude_tool_id,
        )
        if existing_tool is not None:
            raise ValueError("当前项目内已存在同名仪器")

    async def get_tags_by_ids(self, tag_ids: List[int]) -> List[ToolTag]:
        if not tag_ids:
            return []
        result = await self.db.execute(select(ToolTag).where(ToolTag.id.in_(tag_ids)))
        return result.scalars().all()

    async def _validate_project_id(self, project_id: Optional[int]) -> None:
        if project_id is None:
            return
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        if not getattr(project, "active", True):
            raise ValueError("Project is inactive")

    @classmethod
    def _normalize_match_text(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        text = unicodedata.normalize("NFKC", str(value)).lower()
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
        text = re.sub(r"_+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _compact_match_text(value: str) -> str:
        return re.sub(r"\s+", "", value or "")

    @classmethod
    def _extract_match_tokens(cls, normalized_text: str) -> List[str]:
        tokens: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized_text or ""):
            token = match.group(0).strip()
            if not token or token in seen:
                continue
            if token in cls._SUGGEST_STOPWORDS:
                continue
            if re.fullmatch(r"[a-z]", token):
                continue
            if token.isdigit() and len(token) <= 1:
                continue
            seen.add(token)
            tokens.append(token)
        return tokens

    @staticmethod
    def _is_security_server_project(project: Project) -> bool:
        app_id = (getattr(project, "application_identifier", None) or "").strip()
        return app_id.startswith("security-server:")

    @classmethod
    def _score_project_for_tool(
        cls,
        *,
        project: Project,
        tool_name_text: str,
        all_tool_text: str,
        all_tool_compact: str,
    ) -> Optional[ToolProjectSuggestCandidate]:
        project_name = (getattr(project, "name", None) or "").strip()
        if not project_name:
            return None

        project_name_text = cls._normalize_match_text(project_name)
        if not project_name_text:
            return None
        project_name_compact = cls._compact_match_text(project_name_text)

        score = 0
        reason_parts: list[str] = []

        if tool_name_text and project_name_text == tool_name_text:
            score += 140
            reason_parts.append("项目名与仪器名完全一致")
        elif tool_name_text and project_name_compact and project_name_compact in cls._compact_match_text(tool_name_text):
            score += 90
            reason_parts.append("项目名命中仪器名称")
        elif project_name_compact and project_name_compact in all_tool_compact:
            score += 75
            reason_parts.append("项目名命中仪器信息")

        project_tokens = cls._extract_match_tokens(project_name_text)
        matched_tokens: list[str] = []
        token_score = 0
        for token in project_tokens:
            token_compact = cls._compact_match_text(token)
            if not token_compact:
                continue
            if token in all_tool_text or token_compact in all_tool_compact:
                matched_tokens.append(token)
                token_score += min(10 + len(token_compact) * 4, 24)

        if matched_tokens:
            score += min(token_score, 70)
            if len(matched_tokens) >= 2:
                score += 10
            reason_parts.append(f"关键词匹配: {'/'.join(matched_tokens[:3])}")

        if cls._is_security_server_project(project):
            score += 5

        if score <= 0:
            return None

        return ToolProjectSuggestCandidate(
            project_id=int(project.id),
            project_name=project_name,
            score=int(score),
            reason="；".join(reason_parts) if reason_parts else "弱匹配",
        )

    async def suggest_project_for_tool(
        self, payload: ToolProjectSuggestRequest
    ) -> ToolProjectSuggestResponse:
        tool_name_text = self._normalize_match_text(payload.name)
        location_text = self._normalize_match_text(payload.location)
        description_text = self._normalize_match_text(payload.description)
        all_tool_text = " ".join(
            part for part in [tool_name_text, location_text, description_text] if part
        ).strip()
        all_tool_compact = self._compact_match_text(all_tool_text)

        result = await self.db.execute(
            select(Project).where(Project.active == True)  # noqa: E712
        )
        projects = list(result.scalars().all())
        if not projects:
            return ToolProjectSuggestResponse(
                matched=False,
                reason="暂无可用项目（本地镜像为空）",
            )

        security_projects = [p for p in projects if self._is_security_server_project(p)]
        if security_projects:
            projects = security_projects

        candidates: list[ToolProjectSuggestCandidate] = []
        for project in projects:
            candidate = self._score_project_for_tool(
                project=project,
                tool_name_text=tool_name_text,
                all_tool_text=all_tool_text,
                all_tool_compact=all_tool_compact,
            )
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda item: (-item.score, item.project_name))
        top_candidates = candidates[:5]

        if not top_candidates:
            return ToolProjectSuggestResponse(
                matched=False,
                reason="未找到可匹配的项目，请手动选择",
                candidates=[],
            )

        best = top_candidates[0]
        second = top_candidates[1] if len(top_candidates) > 1 else None

        if best.score < 45:
            return ToolProjectSuggestResponse(
                matched=False,
                score=best.score,
                reason="匹配度较低，请人工确认",
                candidates=top_candidates,
            )

        if second and best.score < 90 and (best.score - second.score) <= 8:
            return ToolProjectSuggestResponse(
                matched=False,
                score=best.score,
                reason=f"候选项目接近（{best.project_name} / {second.project_name}），请人工确认",
                candidates=top_candidates,
            )

        return ToolProjectSuggestResponse(
            matched=True,
            project_id=best.project_id,
            project_name=best.project_name,
            score=best.score,
            reason=best.reason or "已匹配",
            candidates=top_candidates,
        )
    
    async def create_tool(self, tool_in: ToolCreate) -> Tool:
        """创建工具"""
        data = tool_in.model_dump()
        tag_ids = data.pop("tag_ids", None)
        await self._validate_project_id(data.get("project_id"))
        await self.ensure_tool_name_available(
            name=data.get("name"),
            project_id=data.get("project_id"),
        )
        tool = Tool(
            name=data.get("name"),
            visible=data.get("visible", True),
            operational=data.get("operational", False),
            requires_reservation=data.get("requires_reservation", True),
            description=data.get("description", ""),
            _location=data.get("location"),
            _phone_number=data.get("phone_number"),
            _primary_owner_id=data.get("primary_owner_id"),
            category_id=data.get("category_id"),
            project_id=data.get("project_id"),
            price_type=data.get("price_type", 1),
            price_per_use=data.get("price_per_use", 0),
            price_per_hour=data.get("price_per_hour", 0),
            maximum_reservations_per_day=data.get("maximum_reservations_per_day"),
        )
        if tag_ids is not None:
            tags = await self.get_tags_by_ids(tag_ids)
            tool.tags = tags
        self.db.add(tool)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if self._is_tool_name_integrity_error(exc):
                raise ValueError("当前项目内已存在同名仪器") from exc
            raise
        return await self.get_tool(tool.id)
    
    async def update_tool(self, tool_id: int, tool_in: ToolUpdate) -> Optional[Tool]:
        """更新工具"""
        tool = await self.get_tool(tool_id)
        if not tool:
            return None
        
        update_data = tool_in.model_dump(exclude_unset=True)
        tag_ids = update_data.pop("tag_ids", None) if "tag_ids" in update_data else None
        should_recalculate_usage_amounts = any(
            field in update_data for field in ("price_type", "price_per_use", "price_per_hour")
        )
        
        # 处理特殊字段映射
        if "location" in update_data:
            tool._location = update_data.pop("location")
        if "phone_number" in update_data:
            tool._phone_number = update_data.pop("phone_number")
        if "project_id" in update_data:
            await self._validate_project_id(update_data["project_id"])

        target_name = update_data.get("name", tool.name)
        target_project_id = update_data.get("project_id", tool.project_id)
        if "name" in update_data or "project_id" in update_data:
            await self.ensure_tool_name_available(
                name=target_name,
                project_id=target_project_id,
                exclude_tool_id=tool_id,
            )
        
        for field, value in update_data.items():
            setattr(tool, field, value)
        if tag_ids is not None:
            tags = await self.get_tags_by_ids(tag_ids)
            tool.tags = tags

        if should_recalculate_usage_amounts:
            await UsageEventService.recalculate_amounts_for_tool(
                self.db,
                tool_id,
                tool=tool,
            )

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if self._is_tool_name_integrity_error(exc):
                raise ValueError("当前项目内已存在同名仪器") from exc
            raise
        return await self.get_tool(tool_id)

    async def get_categories(self) -> List[ToolCategory]:
        result = await self.db.execute(select(ToolCategory).order_by(ToolCategory.name.asc()))
        return result.scalars().all()

    async def create_category(self, name: str) -> ToolCategory:
        category = ToolCategory(name=name)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update_category(self, category_id: int, name: str) -> Optional[ToolCategory]:
        result = await self.db.execute(select(ToolCategory).where(ToolCategory.id == category_id))
        category = result.scalar_one_or_none()
        if not category:
            return None
        category.name = name
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete_category(self, category_id: int) -> bool:
        result = await self.db.execute(select(ToolCategory).where(ToolCategory.id == category_id))
        category = result.scalar_one_or_none()
        if not category:
            return False
        await self.db.delete(category)
        await self.db.commit()
        return True

    async def get_tags(self) -> List[ToolTag]:
        result = await self.db.execute(select(ToolTag).order_by(ToolTag.name.asc()))
        return result.scalars().all()

    async def create_tag(self, name: str) -> ToolTag:
        tag = ToolTag(name=name)
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def update_tag(self, tag_id: int, name: str) -> Optional[ToolTag]:
        result = await self.db.execute(select(ToolTag).where(ToolTag.id == tag_id))
        tag = result.scalar_one_or_none()
        if not tag:
            return None
        tag.name = name
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: int) -> bool:
        result = await self.db.execute(select(ToolTag).where(ToolTag.id == tag_id))
        tag = result.scalar_one_or_none()
        if not tag:
            return False
        await self.db.delete(tag)
        await self.db.commit()
        return True
    
    async def delete_tool(self, tool_id: int) -> bool:
        """删除仪器"""
        tool = await self.get_tool(tool_id)
        if not tool:
            return False

        # 级联清理该仪器在 media/tools/{id}/ 下的所有图片
        from app.core.media import remove_entity_dir
        remove_entity_dir("tools", tool_id)

        await self.db.delete(tool)
        await self.db.commit()
        return True

    async def get_current_usage(self, tool_id: int) -> Optional[UsageEvent]:
        """获取工具当前的使用记录"""
        query = select(UsageEvent).where(
            and_(
                UsageEvent.tool_id == tool_id,
                UsageEvent.end == None
            )
        ).order_by(desc(UsageEvent.start))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def _get_usage_event_for_response(self, usage_event_id: int) -> Optional[UsageEvent]:
        """Load usage event with relationships needed by UsageEventResponse serialization."""
        result = await self.db.execute(
            select(UsageEvent)
            .options(
                selectinload(UsageEvent.user),
                selectinload(UsageEvent.operator),
                selectinload(UsageEvent.tool),
                selectinload(UsageEvent.project),
            )
            .where(UsageEvent.id == usage_event_id)
        )
        return result.scalar_one_or_none()

    async def enable_tool(self, tool_id: int, enable_data: ToolEnable, operator_id: int) -> UsageEvent:
        """启用工具"""
        # 1. 锁定仪器行，串行化同一仪器的启停写入
        tool = await UsageEventService._lock_tool_for_usage(self.db, tool_id)
        if not tool:
            raise ValueError("Tool not found")

        usage_user = await self.db.get(User, enable_data.user_id)
        if not usage_user:
            raise ValueError("User not found")
        if not getattr(usage_user, "is_active", True):
            raise ValueError("User is inactive")
        if self._is_external_user(usage_user) and not getattr(usage_user, "is_verified", False):
            raise ValueError("User is not verified")
        if not await self.check_external_user_tool_access(tool_id, usage_user):
            raise ValueError("您没有使用该仪器的权限，请联系管理员申请授权")

        # 2. 在锁内复查工具是否正在使用
        current_usage = await UsageEventService.get_active_usage_for_tool(
            self.db,
            tool_id,
            lock_rows=True,
        )
        if current_usage:
            raise ValueError("Tool is already in use")

        # 3. 创建使用记录
        project_id = enable_data.project_id or getattr(tool, "project_id", None)
        if project_id is None:
            raise ValueError("Tool has no bound project configured")
        payer_account = await AccountService.resolve_reservable_account_for_user(
            self.db,
            enable_data.user_id,
            project_id=int(project_id),
            require_reservable=False,
        )
        if payer_account is None:
            if self._is_external_user(usage_user):
                raise ValueError("当前外部用户尚未配置所属账户，请联系管理员配置，或先申请加入账户并等待审批生效")
            raise ValueError("当前使用用户没有可用的付款账户")
        usage_event = UsageEvent(
            tool_id=tool_id,
            user_id=enable_data.user_id,
            project_id=project_id,
            operator_id=operator_id,
            payer_account_id=payer_account.id,
            start=datetime.utcnow(),
            note=enable_data.note,
            has_ended=0
        )
        
        self.db.add(usage_event)
        await self.db.commit()
        await self.db.refresh(usage_event)
        loaded = await self._get_usage_event_for_response(usage_event.id)
        return loaded or usage_event

    async def disable_tool(self, tool_id: int, disable_data: ToolDisable) -> UsageEvent:
        """禁用工具"""
        # 1. 锁定仪器行，并在锁内获取当前使用记录
        tool = await UsageEventService._lock_tool_for_usage(self.db, tool_id)
        if not tool:
            raise ValueError("Tool not found")
        current_usage = await UsageEventService.get_active_usage_for_tool(
            self.db,
            tool_id,
            lock_rows=True,
        )
        if not current_usage:
            raise ValueError("Tool is not in use")

        # 2. 更新结束时间
        current_usage.end = datetime.utcnow()
        
        # 计算 has_ended: max(has_ended) + 1
        query = select(func.max(UsageEvent.has_ended)).where(UsageEvent.tool_id == tool_id)
        result = await self.db.execute(query)
        max_has_ended = result.scalar() or 0
        current_usage.has_ended = max_has_ended + 1
        
        if disable_data.note:
            current_usage.note = disable_data.note
        if disable_data.run_data:
            current_usage.run_data = disable_data.run_data

        await self.db.commit()
        await self.db.refresh(current_usage)
        loaded = await self._get_usage_event_for_response(current_usage.id)
        return loaded or current_usage
