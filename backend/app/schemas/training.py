from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TrainingContentType = Literal["link", "document", "video"]


class TrainingCategoryBase(BaseModel):
    name: str


class TrainingCategoryCreate(TrainingCategoryBase):
    pass


class TrainingCategoryResponse(TrainingCategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TrainingCourseBase(BaseModel):
    title: str
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    category_id: Optional[int] = None
    sort_order: int = 0
    published: bool = True


class TrainingCourseCreate(TrainingCourseBase):
    pass


class TrainingCourseUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    category_id: Optional[int] = None
    sort_order: Optional[int] = None
    published: Optional[bool] = None


class TrainingCourseResponse(TrainingCourseBase):
    id: int
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingChapterBase(BaseModel):
    course_id: int
    title: str
    summary: Optional[str] = None
    sort_order: int = 0
    published: bool = True


class TrainingChapterCreate(TrainingChapterBase):
    pass


class TrainingChapterUpdate(BaseModel):
    course_id: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    sort_order: Optional[int] = None
    published: Optional[bool] = None


class TrainingChapterResponse(TrainingChapterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingContentBase(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    category_id: Optional[int] = None
    chapter_id: Optional[int] = None
    content_type: TrainingContentType = "link"
    sort_order: int = 0
    estimated_minutes: int = Field(0, ge=0)
    published: bool = True


class TrainingContentCreate(TrainingContentBase):
    pass


class TrainingContentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None
    category_id: Optional[int] = None
    chapter_id: Optional[int] = None
    content_type: Optional[TrainingContentType] = None
    sort_order: Optional[int] = None
    estimated_minutes: Optional[int] = Field(None, ge=0)
    published: Optional[bool] = None


class TrainingContentResponse(TrainingContentBase):
    id: int
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingRecordCreate(BaseModel):
    content_id: int
    completed_at: Optional[datetime] = None


class TrainingRecordResponse(BaseModel):
    id: int
    user_id: int
    content_id: int
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingContentProgressResponse(TrainingContentResponse):
    learned: bool = False
    learned_at: Optional[datetime] = None


class TrainingChapterDetailResponse(TrainingChapterResponse):
    materials: List[TrainingContentProgressResponse] = []
    total_materials: int = 0
    completed_materials: int = 0
    progress_percent: float = 0.0


class TrainingCourseDetailResponse(TrainingCourseResponse):
    chapters: List[TrainingChapterDetailResponse] = []
    total_materials: int = 0
    completed_materials: int = 0
    progress_percent: float = 0.0


class TrainingOverviewResponse(BaseModel):
    courses: List[TrainingCourseDetailResponse]
    standalone_contents: List[TrainingContentProgressResponse]
    total_materials: int
    completed_materials: int
    progress_percent: float


class ExamQuestionBase(BaseModel):
    category_id: Optional[int] = None
    question: str
    options: Optional[List[str]] = None
    answer: Optional[Any] = None
    score: int = 1
    type: Literal["single", "multi", "truefalse"] = "single"


class ExamQuestionCreate(ExamQuestionBase):
    answer: Any


class ExamQuestionUpdate(BaseModel):
    category_id: Optional[int] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None
    score: Optional[int] = None
    type: Optional[Literal["single", "multi", "truefalse"]] = None


class ExamQuestionResponse(ExamQuestionBase):
    id: int
    project_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExamQuestionPublic(BaseModel):
    id: int
    category_id: Optional[int] = None
    question: str
    options: Optional[List[str]] = None
    score: int = 1
    type: str


class ExamRuleBase(BaseModel):
    pass_score: int = 60
    question_count: int = 10
    duration_minutes: int = 30


class ExamRuleCreate(ExamRuleBase):
    pass


class ExamRuleUpdate(BaseModel):
    pass_score: Optional[int] = None
    question_count: Optional[int] = None
    duration_minutes: Optional[int] = None


class ExamRuleResponse(ExamRuleBase):
    id: int
    project_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExamStartResponse(BaseModel):
    attempt_id: int
    questions: List[ExamQuestionPublic]
    pass_score: int
    duration_minutes: int
    remaining_minutes: Optional[int] = None
    started_at: Optional[datetime] = None


class ExamSubmitRequest(BaseModel):
    answers: Dict[int, Any]


class ExamSubmitResponse(BaseModel):
    attempt_id: int
    score: int
    passed: bool
