"""
媒体文件目录工具

约定：
- 每个实体（用户/仪器/公告）在 media 下各有独立命名空间
- 每个具体实体再以 id 为子目录，所有与它相关的图片都落在此子目录中
- 实体删除时，级联删除其整个子目录
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Literal, Optional

import aiofiles
from fastapi import HTTPException, UploadFile

from app.core.config import (
    ANNOUNCEMENTS_MEDIA_DIR,
    BACKEND_ROOT,
    COLLABORATION_MEDIA_DIR,
    MEDIA_ROOT,
    TOOLS_MEDIA_DIR,
    TRAINING_MEDIA_DIR,
    USERS_MEDIA_DIR,
    settings,
)

EntityKind = Literal["users", "tools", "announcements", "training", "collaboration"]
logger = logging.getLogger(__name__)
_UPLOAD_CHUNK_SIZE = 1024 * 1024

_KIND_TO_ROOT = {
    "users": USERS_MEDIA_DIR,
    "tools": TOOLS_MEDIA_DIR,
    "announcements": ANNOUNCEMENTS_MEDIA_DIR,
    "training": TRAINING_MEDIA_DIR,
    "collaboration": COLLABORATION_MEDIA_DIR,
}


def entity_dir(kind: EntityKind, entity_id: int) -> Path:
    """返回某个实体对应的绝对目录路径；不会触发创建"""
    return _KIND_TO_ROOT[kind] / str(entity_id)


def ensure_entity_dir(kind: EntityKind, entity_id: int) -> Path:
    """返回目录并确保其存在"""
    path = entity_dir(kind, entity_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_url(kind: EntityKind, entity_id: int, filename: str) -> str:
    """返回可被前端使用的 /media/... URL"""
    return f"/media/{kind}/{entity_id}/{filename}"


def remove_entity_dir(kind: EntityKind, entity_id: int) -> None:
    """级联删除实体子目录；目录不存在时静默跳过"""
    path = entity_dir(kind, entity_id)
    if path.exists() and path.is_dir():
        try:
            # 安全检查：确保位于预期根路径内
            resolved = path.resolve()
            root = _KIND_TO_ROOT[kind].resolve()
            if root in resolved.parents or resolved == root:
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            # 清理失败不应阻塞主业务流程
            pass


async def save_image_upload(
    kind: EntityKind,
    entity_id: int,
    file: UploadFile,
    *,
    max_size_mb: Optional[int] = None,
    allowed_types: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    校验并保存单张图片到实体子目录下。

    返回 (filename, url)：
    - filename: 仅文件名，例如 "abc123.jpg"
    - url: 可被前端使用的 URL，例如 "/media/tools/12/abc123.jpg"
    """
    allowed = allowed_types or settings.TOOL_IMAGE_ALLOWED_TYPES
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    limit = (max_size_mb or settings.TOOL_IMAGE_MAX_SIZE_MB) * 1024 * 1024

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if not ext:
        ext = ".jpg"
    filename = f"{uuid.uuid4().hex[:12]}{ext}"

    target_path = await _prepare_upload_target(kind, entity_id, filename)
    await _save_upload_file_with_timeout(
        file=file,
        target_path=target_path,
        limit_bytes=limit,
        too_large_detail=f"文件过大，最大 {max_size_mb or settings.TOOL_IMAGE_MAX_SIZE_MB}MB",
    )
    return filename, relative_url(kind, entity_id, filename)


async def save_file_upload(
    kind: EntityKind,
    entity_id: int,
    file: UploadFile,
    *,
    max_size_mb: int,
    allowed_content_types: list[str],
) -> tuple[str, str]:
    """校验并保存通用文件到实体子目录下。"""
    if file.content_type and file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    limit = max_size_mb * 1024 * 1024

    ext = Path(file.filename).suffix.lower() if file.filename else ""
    filename = f"{uuid.uuid4().hex[:12]}{ext}"

    target_path = await _prepare_upload_target(kind, entity_id, filename)
    await _save_upload_file_with_timeout(
        file=file,
        target_path=target_path,
        limit_bytes=limit,
        too_large_detail=f"文件过大，最大 {max_size_mb}MB",
    )
    return filename, relative_url(kind, entity_id, filename)


async def _prepare_upload_target(kind: EntityKind, entity_id: int, filename: str) -> Path:
    timeout = max(float(settings.MEDIA_WRITE_TIMEOUT_SECONDS or 30.0), 1.0)
    try:
        target_dir = await asyncio.wait_for(
            asyncio.to_thread(ensure_entity_dir, kind, entity_id),
            timeout=timeout,
        )
    except TimeoutError as exc:
        logger.error("Timed out creating media directory kind=%s entity_id=%s", kind, entity_id)
        raise HTTPException(status_code=504, detail="媒体目录创建超时，请检查后端存储卷") from exc
    except OSError as exc:
        logger.exception("Failed to create media directory kind=%s entity_id=%s", kind, entity_id)
        raise HTTPException(status_code=500, detail="媒体目录创建失败，请检查后端存储卷") from exc
    return target_dir / filename


async def _save_upload_file_with_timeout(
    *,
    file: UploadFile,
    target_path: Path,
    limit_bytes: int,
    too_large_detail: str,
) -> None:
    timeout = max(float(settings.MEDIA_WRITE_TIMEOUT_SECONDS or 30.0), 1.0)
    try:
        await asyncio.wait_for(
            _save_upload_file_streaming(
                file,
                target_path,
                limit_bytes=limit_bytes,
                too_large_detail=too_large_detail,
            ),
            timeout=timeout,
        )
    except TimeoutError as exc:
        target_path.unlink(missing_ok=True)
        logger.error("Timed out saving uploaded media file to %s", target_path)
        raise HTTPException(status_code=504, detail="媒体文件保存超时，请检查后端存储卷") from exc


async def _save_upload_file_streaming(
    file: UploadFile,
    target_path: Path,
    *,
    limit_bytes: int,
    too_large_detail: str,
) -> None:
    """Stream upload content to disk without blocking the event loop."""
    written = 0
    try:
        async with aiofiles.open(target_path, "wb") as out:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit_bytes:
                    raise HTTPException(status_code=400, detail=too_large_detail)
                await out.write(chunk)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        target_path.unlink(missing_ok=True)
        logger.exception("Failed to save uploaded media file to %s", target_path)
        raise HTTPException(status_code=500, detail="媒体文件保存失败，请检查后端存储卷") from exc
    finally:
        await file.close()


def resolve_tool_image_path(stored_value: str | None) -> Path | None:
    """根据数据库中存放的图片路径解析到本地文件绝对路径。"""
    if not stored_value:
        return None
    if stored_value.startswith("/media/"):
        return MEDIA_ROOT / stored_value.removeprefix("/media/")
    if "/" in stored_value:
        return MEDIA_ROOT / stored_value
    return None


def remove_tool_image_file(stored_value: str | None) -> None:
    """删除单张仪器图片文件；文件不存在时静默跳过。"""
    path = resolve_tool_image_path(stored_value)
    if path is None:
        return
    path.unlink(missing_ok=True)


def resolve_media_path(stored_value: str | None) -> Path | None:
    """根据 /media/... 或 media 相对路径解析到本地绝对路径。"""
    if not stored_value:
        return None
    if stored_value.startswith("/media/"):
        return MEDIA_ROOT / stored_value.removeprefix("/media/")
    if stored_value.startswith("media/"):
        return BACKEND_ROOT / stored_value
    if "/" in stored_value:
        return MEDIA_ROOT / stored_value
    return None


def remove_media_file(stored_value: str | None) -> None:
    """删除单个媒体文件；文件不存在时静默跳过。"""
    path = resolve_media_path(stored_value)
    if path is None:
        return
    path.unlink(missing_ok=True)


def ensure_media_roots() -> None:
    """应用启动时确保根目录存在"""
    for path in (USERS_MEDIA_DIR, TOOLS_MEDIA_DIR, ANNOUNCEMENTS_MEDIA_DIR, TRAINING_MEDIA_DIR, COLLABORATION_MEDIA_DIR):
        path.mkdir(parents=True, exist_ok=True)
