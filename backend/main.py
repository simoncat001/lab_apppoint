"""
NEMO FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings, MEDIA_ROOT
from app.api.api import api_router
from app.api.staff_api import staff_api_router
from app.db.bootstrap import ensure_schema
from app.services.staff.result import StaffBusinessError

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="NEMO Laboratory Logistics Management System API",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    # For local preview, allow the Vite dev server.
    # You can tighten this in production via BACKEND_CORS_ORIGINS.
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000","http://10.1.140.127:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# 注册路由
app.include_router(api_router, prefix=settings.API_PREFIX)
# Ported security-server endpoints — same path layout as the legacy Spring
# service, shifted under /security-api so nginx can proxy them transparently.
app.include_router(staff_api_router, prefix="/security-api/api")


@app.exception_handler(StaffBusinessError)
async def _staff_business_error_handler(_request: Request, exc: StaffBusinessError) -> JSONResponse:
    """Mirror Spring's BusinessException → Result.error(...) behaviour.

    Always returns HTTP 200; the front-end's axios interceptor checks the
    embedded `code` field and surfaces `message` as a toast.
    """
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None},
    )

# 静态文件服务（媒体文件）
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
from app.core.media import ensure_media_roots
ensure_media_roots()
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")

@app.on_event("startup")
async def _startup_schema_bootstrap() -> None:
    # Ensure critical tables/columns exist before serving requests.
    await ensure_schema()


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "NEMO FastAPI Backend",
        "version": settings.VERSION,
        "docs": f"{settings.API_PREFIX}/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
