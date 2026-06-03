"""Top-level router for the ported security-server endpoints.

Mounted by main.py at `/security-api/api`, so the externally-visible URLs
are `/security-api/api/login`, `/security-api/api/departments/list`, etc.
This matches the legacy Spring controller paths (`/api/...`) shifted under
the `/security-api` prefix that nginx forwards as-is.

The existing `security-server-ui` only needs to set `VITE_API_BASE=/security-api`
to switch from the old Java service to this FastAPI port.
"""

from fastapi import APIRouter

from app.api.endpoints.staff import (
    applications,
    auth,
    departments,
    groups,
    projects,
    users,
)

staff_api_router = APIRouter()

# AuthController mapped at /api → login/register/logout live at root
staff_api_router.include_router(auth.router, tags=["staff-auth"])

staff_api_router.include_router(users.router,        prefix="/users",        tags=["staff-users"])
staff_api_router.include_router(departments.router,  prefix="/departments",  tags=["staff-departments"])
staff_api_router.include_router(projects.router,     prefix="/projects",     tags=["staff-projects"])
staff_api_router.include_router(groups.router,       prefix="/groups",       tags=["staff-groups"])
staff_api_router.include_router(applications.router, prefix="/applications", tags=["staff-applications"])
