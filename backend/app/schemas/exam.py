"""Pydantic schemas for the richer exam module (banks, papers, attempts, grading)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["single", "multi", "truefalse", "fill", "essay"]


# ==================== Question Bank ====================


class QuestionBankBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class QuestionBankCreate(QuestionBankBase):
    pass


class QuestionBankUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class QuestionBankResponse(QuestionBankBase):
    id: int
    project_id: Optional[int] = None
    question_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Question (extended) ====================


class ExamQuestionRich(BaseModel):
    """扩展后的题目结构，用于题库管理页面。"""

    id: int
    project_id: Optional[int] = None
    bank_id: Optional[int] = None
    category_id: Optional[int] = None
    question: str
    type: QuestionType
    options: Optional[List[str]] = None
    answer: Optional[Any] = None
    score: int = 1
    difficulty: int = 3
    knowledge_point: Optional[str] = None
    analysis: Optional[str] = None


class ExamQuestionRichCreate(BaseModel):
    bank_id: Optional[int] = None
    category_id: Optional[int] = None
    question: str
    type: QuestionType = "single"
    options: Optional[List[str]] = None
    answer: Any = None
    score: int = Field(1, ge=0)
    difficulty: int = Field(3, ge=1, le=5)
    knowledge_point: Optional[str] = None
    analysis: Optional[str] = None


class ExamQuestionRichUpdate(BaseModel):
    bank_id: Optional[int] = None
    category_id: Optional[int] = None
    question: Optional[str] = None
    type: Optional[QuestionType] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None
    score: Optional[int] = Field(None, ge=0)
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    knowledge_point: Optional[str] = None
    analysis: Optional[str] = None


# ==================== Paper ====================


ComposeType = Literal["manual", "random"]


class PaperQuestionItem(BaseModel):
    """用于手动组卷时指定一道题及其分值。"""

    question_id: int
    sort_order: int = 0
    score_override: Optional[int] = None


class PaperRuleItem(BaseModel):
    """用于随机组卷时的抽题规则。"""

    bank_id: Optional[int] = None
    question_type: Optional[QuestionType] = None
    difficulty_min: int = Field(1, ge=1, le=5)
    difficulty_max: int = Field(5, ge=1, le=5)
    count: int = Field(1, ge=1)
    score_per_question: int = Field(1, ge=0)
    knowledge_point: Optional[str] = None


class PaperRuleResponse(PaperRuleItem):
    id: int
    paper_id: int
    model_config = ConfigDict(from_attributes=True)


class PaperQuestionResponse(BaseModel):
    id: int
    paper_id: int
    question_id: int
    sort_order: int
    score_override: Optional[int] = None
    question: Optional[ExamQuestionRich] = None

    model_config = ConfigDict(from_attributes=True)


class ExamPaperBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    compose_type: ComposeType = "manual"
    total_score: int = Field(0, ge=0)
    pass_score: int = Field(60, ge=0)
    duration_minutes: int = Field(30, ge=1)
    show_result_immediately: bool = False
    published: bool = False


class ExamPaperCreate(ExamPaperBase):
    # 可选地在创建时直接附带 manual 题列表或 random 规则
    questions: Optional[List[PaperQuestionItem]] = None
    rules: Optional[List[PaperRuleItem]] = None


class ExamPaperUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    compose_type: Optional[ComposeType] = None
    total_score: Optional[int] = Field(None, ge=0)
    pass_score: Optional[int] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, ge=1)
    show_result_immediately: Optional[bool] = None
    published: Optional[bool] = None
    questions: Optional[List[PaperQuestionItem]] = None
    rules: Optional[List[PaperRuleItem]] = None


class ExamPaperResponse(ExamPaperBase):
    id: int
    project_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    question_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExamPaperDetailResponse(ExamPaperResponse):
    questions: List[PaperQuestionResponse] = []
    rules: List[PaperRuleResponse] = []


class PaperPreviewResponse(BaseModel):
    """组卷预览：按当前 rules 试抽一次，用于管理员校验。"""

    questions: List[ExamQuestionRich]
    total_score: int


# ==================== Attempt / Submission / Grading ====================


class ExamQuestionPublic(BaseModel):
    """给考生的题面，不含 answer/analysis。"""

    id: int
    question: str
    type: QuestionType
    options: Optional[List[str]] = None
    score: int = 1


class ExamStartPaperResponse(BaseModel):
    attempt_id: int
    paper_id: int
    paper_name: str
    total_score: int
    pass_score: int
    duration_minutes: int
    remaining_minutes: Optional[int] = None
    started_at: datetime
    questions: List[ExamQuestionPublic]


class AnswerItemIn(BaseModel):
    question_id: int
    answer: Any


class ExamSubmitPaperRequest(BaseModel):
    answers: List[AnswerItemIn]


class AttemptAnswerItemResponse(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    full_score: int
    answer: Optional[Any] = None
    auto_score: Optional[int] = None
    manual_score: Optional[int] = None
    final_score: Optional[int] = None
    grader_id: Optional[int] = None
    graded_at: Optional[datetime] = None
    comment: Optional[str] = None
    # 阅卷页需要的题目上下文
    question: Optional[ExamQuestionRich] = None

    model_config = ConfigDict(from_attributes=True)


class ExamAttemptSummary(BaseModel):
    id: int
    user_id: int
    paper_id: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: int
    total_score: int
    passed: bool
    manual_graded: bool

    model_config = ConfigDict(from_attributes=True)


class ExamAttemptDetail(ExamAttemptSummary):
    items: List[AttemptAnswerItemResponse] = []


class GradeItemRequest(BaseModel):
    manual_score: int = Field(..., ge=0)
    comment: Optional[str] = None


class GradeBatchItem(BaseModel):
    item_id: int
    manual_score: int = Field(..., ge=0)
    comment: Optional[str] = None


class GradeBatchRequest(BaseModel):
    items: List[GradeBatchItem]


# ==================== Stats ====================


class PaperStatsResponse(BaseModel):
    paper_id: int
    attempt_count: int
    pass_count: int
    pass_rate: float  # 0..1
    avg_score: float
    max_score: int
    min_score: int
