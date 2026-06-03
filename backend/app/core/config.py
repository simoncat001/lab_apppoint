"""
Core configuration settings
"""

from pathlib import Path
from typing import List, Optional
from urllib.parse import quote
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, model_validator

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = BACKEND_ROOT / "media"

# 每一种实体的图片都放在自己的命名空间下，实体再开自己的子目录：
#   media/users/{user_id}/            用户头像
#   media/tools/{tool_id}/            仪器图片
#   media/announcements/{id}/         公告内嵌图片
#   media/training/{content_id}/      培训资料文件
#   media/collaboration/{project_id}/ 科研协作记录富文本媒体
USERS_MEDIA_DIR = MEDIA_ROOT / "users"
TOOLS_MEDIA_DIR = MEDIA_ROOT / "tools"
ANNOUNCEMENTS_MEDIA_DIR = MEDIA_ROOT / "announcements"
TRAINING_MEDIA_DIR = MEDIA_ROOT / "training"
COLLABORATION_MEDIA_DIR = MEDIA_ROOT / "collaboration"

# 历史路径（旧版公告图片落在这里），保留只读兼容
LEGACY_UPLOAD_DIR = MEDIA_ROOT / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=BACKEND_ROOT / ".env",
        extra="ignore",
    )
    # 项目信息
    PROJECT_NAME: str = "NEMO FastAPI Backend"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    # Backward-compatible alias (historical name)
    API_V1_STR: str = "/api"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # MySQL 数据库配置
    MYSQL_SERVER: str = "127.0.0.1"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "12345678"
    MYSQL_DB: str = "szlab_appoint"
    MYSQL_PORT: int = 3306

    DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def assemble_database_url(self):
        if self.DATABASE_URL:
            return self

        user = quote(self.MYSQL_USER, safe="")
        password = quote(self.MYSQL_PASSWORD, safe="")
        self.DATABASE_URL = (
            f"mysql+aiomysql://{user}:{password}@"
            f"{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )
        return self
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # 内部员工模块（原 security-server）。endpoints 已经融合进本进程，挂在
    # /security-api/api/*。这里只剩两个布尔开关，让运维可以紧急关闭。原来
    # 的 HTTP 客户端配置（BASE_URL / LOGIN_PATH / TIMEOUT / VERIFY_SSL /
    # SERVICE_*）已废弃，pydantic-settings 的 `extra="ignore"` 会安静地
    # 吃掉残留在旧 .env 里的这些键。
    SECURITY_SERVER_ENABLED: bool = True
    SECURITY_SERVER_PROJECT_SYNC_ENABLED: bool = True

    # 预约设置
    RESERVATION_CANCEL_LIMIT_PER_MONTH: Optional[int] = 3
    RESERVATION_REQUIRE_PAYMENT: bool = False

    # 验证码设置
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 10
    VERIFICATION_CODE_RETURN_IN_RESPONSE: bool = False
    REQUIRE_VERIFICATION_FOR_REGISTER: bool = False

    # 考试默认设置
    EXAM_DEFAULT_PASS_SCORE: int = 60
    EXAM_DEFAULT_QUESTION_COUNT: int = 10
    EXAM_DEFAULT_DURATION_MINUTES: int = 30

    
    # 图片上传限制（同时用于 tool / announcement 等所有图片端点的默认值）
    TOOL_IMAGE_MAX_SIZE_MB: int = 20
    TOOL_IMAGE_ALLOWED_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    MEDIA_WRITE_TIMEOUT_SECONDS: float = 30.0

    # 培训资料上传限制
    TRAINING_DOCUMENT_MAX_SIZE_MB: int = 30
    TRAINING_VIDEO_MAX_SIZE_MB: int = 300

    # 科研协作记录富文本媒体上传限制
    COLLABORATION_VIDEO_MAX_SIZE_MB: int = 300
    COLLABORATION_VIDEO_ALLOWED_TYPES: list = ["video/mp4", "video/webm", "video/ogg", "video/quicktime"]

    # 超级管理员
    FIRST_SUPERUSER: str = "admin@nemo.local"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    
settings = Settings()
