from typing import List, Optional
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate


class AnnouncementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_announcements(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
        include_unpublished: bool = False,
    ) -> List[Announcement]:
        query = (
            select(Announcement)
            .options(selectinload(Announcement.author))
            .where(Announcement.project_id == project_id)
        )
        if not include_unpublished:
            query = query.where(Announcement.published == True)
        result = await self.db.execute(query.order_by(Announcement.created_at.desc()).offset(skip).limit(limit))
        return result.scalars().all()

    async def count_announcements(
        self,
        project_id: int,
        include_unpublished: bool = False,
    ) -> int:
        query = select(func.count(Announcement.id)).where(Announcement.project_id == project_id)
        if not include_unpublished:
            query = query.where(Announcement.published == True)
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def get_announcement(self, announcement_id: int, project_id: int) -> Optional[Announcement]:
        result = await self.db.execute(
            select(Announcement)
            .options(selectinload(Announcement.author))
            .where(
                Announcement.id == announcement_id,
                Announcement.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_announcement(
        self,
        data: AnnouncementCreate,
        author_id: Optional[int],
        project_id: int,
    ) -> Announcement:
        announcement = Announcement(
            title=data.title,
            content=data.content,
            published=data.published,
            author_id=author_id,
            project_id=project_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(announcement)
        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def update_announcement(
        self,
        announcement_id: int,
        data: AnnouncementUpdate,
        project_id: int,
    ) -> Optional[Announcement]:
        announcement = await self.get_announcement(announcement_id, project_id)
        if not announcement:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(announcement, field, value)
        announcement.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def delete_announcement(self, announcement_id: int, project_id: int) -> bool:
        announcement = await self.get_announcement(announcement_id, project_id)
        if not announcement:
            return False
        await self.db.delete(announcement)
        await self.db.commit()

        # 级联清理该公告在 media/announcements/{id}/ 下的所有内嵌图片
        from app.core.media import remove_entity_dir
        remove_entity_dir("announcements", announcement_id)
        return True
