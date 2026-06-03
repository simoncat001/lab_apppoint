"""Staff (internal employee) ORM models.

These tables come from the legacy security-server. They live in the same
database as the nemo tables (`szlab_appoint`) but are prefixed with
`staff_` so they don't collide with nemo's own user/project/role tables.
"""

from app.models.staff.user import StaffUser
from app.models.staff.department import StaffDepartment
from app.models.staff.project import StaffProject
from app.models.staff.group import StaffGroup
from app.models.staff.role import StaffRole
from app.models.staff.department_user import StaffDepartmentUser
from app.models.staff.project_user import StaffProjectUser
from app.models.staff.group_user import StaffGroupUser
from app.models.staff.application_request import StaffApplicationRequest
from app.models.staff.user_role import StaffUserRole

__all__ = [
    "StaffUser",
    "StaffDepartment",
    "StaffProject",
    "StaffGroup",
    "StaffRole",
    "StaffDepartmentUser",
    "StaffProjectUser",
    "StaffGroupUser",
    "StaffApplicationRequest",
    "StaffUserRole",
]
