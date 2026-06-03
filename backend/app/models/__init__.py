"""
Initialize all models
"""

from app.db.session import Base
from app.models.user import User
from app.models.tool import Tool
from app.models.tool_image import ToolImage
from app.models.tool_category import ToolCategory
from app.models.tool_tag import ToolTag
from app.models.reservation import Reservation
from app.models.project import Project, ProjectJoinRequest
from app.models.account import Account, AccountType, AccountMembershipChangeRequest
from app.models.bill import Bill
from app.models.usage_event import UsageEvent
from app.models.task import Task, TaskCategory, TaskHistory, TaskUrgency, TaskCategoryStage
from app.models.staff_charge import StaffCharge
from app.models.configuration import Configuration, ConfigurationOption, ConfigurationHistory
from app.models.tool_rate import ToolRate
from app.models.verification_code import VerificationCode
from app.models.announcement import Announcement
from app.models.training import (
    TrainingCategory,
    TrainingCourse,
    TrainingChapter,
    TrainingContent,
    TrainingRecord,
    ExamQuestion,
    ExamRule,
    ExamAttempt,
)
from app.models.exam import (
    QuestionBank,
    ExamPaper,
    ExamPaperQuestion,
    ExamPaperRule,
    ExamAnswerItem,
)
from app.models.maintenance import MaintenanceRecord
from app.models.audit_log import AuditLog
from app.models.tool_user_access import ToolUserAccess
from app.models.collaboration import CollaborationRecord
# Staff (internal employee) tables ported from security-server. Importing
# the subpackage is enough — its __init__ registers each ORM class with Base.
from app.models import staff as _staff  # noqa: F401
from app.models.staff import (
    StaffUser,
    StaffDepartment,
    StaffProject,
    StaffGroup,
    StaffRole,
    StaffDepartmentUser,
    StaffProjectUser,
    StaffGroupUser,
    StaffApplicationRequest,
    StaffUserRole,
)

__all__ = [
    "User",
    "Tool",
    "ToolImage",
    "ToolCategory",
    "ToolTag",
    "ToolRate",
    "Reservation",
    "Project",
    "ProjectJoinRequest",
    "Account",
    "AccountType",
    "AccountMembershipChangeRequest",
    "Bill",
    "UsageEvent",
    "Task",
    "TaskCategory",
    "TaskHistory",
    "TaskUrgency",
    "TaskCategoryStage",
    "StaffCharge",
    "Configuration",
    "ConfigurationOption",
    "ConfigurationHistory",
    "VerificationCode",
    "Announcement",
    "TrainingCategory",
    "TrainingCourse",
    "TrainingChapter",
    "TrainingContent",
    "TrainingRecord",
    "ExamQuestion",
    "ExamRule",
    "ExamAttempt",
    "QuestionBank",
    "ExamPaper",
    "ExamPaperQuestion",
    "ExamPaperRule",
    "ExamAnswerItem",
    "MaintenanceRecord",
    "AuditLog",
    "ToolUserAccess",
    "CollaborationRecord",
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
