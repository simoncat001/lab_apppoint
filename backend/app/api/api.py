"""API router (unversioned)."""

from fastapi import APIRouter
from app.api.endpoints import (
    users,
    tools,
    reservations,
    auth,
    accounts,
    usage_events,
    tasks,
    staff_charges,
    configurations,
    projects,
    billing,
    dashboard,
    announcements,
    training,
    exam,
    maintenance,
    reports,
    integrations,
    upload,
    collaboration,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(usage_events.router, prefix="/usage-events", tags=["usage-events"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(staff_charges.router, prefix="/staff-charges", tags=["staff-charges"])
api_router.include_router(configurations.router, prefix="/configurations", tags=["configurations"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
api_router.include_router(exam.router, prefix="/exams", tags=["exams"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(collaboration.router, prefix="/collaboration-records", tags=["collaboration-records"])
