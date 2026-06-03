"""
通用文件上传端点

注意：公告内嵌图片已迁移至 /api/announcements/{id}/image
本端点仅保留作为向后兼容和未绑定实体时的临时通道，不建议新增用法。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    【已弃用】请使用实体专属的上传端点：
    - 公告内嵌图片：POST /api/announcements/{id}/image
    - 仪器图片：POST /api/tools/{id}/image
    """
    raise HTTPException(
        status_code=410,
        detail="通用图片上传已停用，请改用 /api/announcements/{id}/image 或 /api/tools/{id}/image",
    )
