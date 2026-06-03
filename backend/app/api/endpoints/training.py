import json
from datetime import datetime
from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.core.config import settings
from app.core.media import remove_media_file, save_file_upload
from app.db.session import get_db
from app.models.user import User
from app.schemas.training import (
    TrainingCategoryCreate,
    TrainingCategoryResponse,
    TrainingCourseCreate,
    TrainingCourseUpdate,
    TrainingCourseResponse,
    TrainingChapterCreate,
    TrainingChapterUpdate,
    TrainingChapterResponse,
    TrainingContentCreate,
    TrainingContentUpdate,
    TrainingContentResponse,
    TrainingOverviewResponse,
    TrainingRecordCreate,
    TrainingRecordResponse,
    ExamQuestionCreate,
    ExamQuestionUpdate,
    ExamQuestionResponse,
    ExamQuestionPublic,
    ExamRuleCreate,
    ExamRuleUpdate,
    ExamRuleResponse,
    ExamStartResponse,
    ExamSubmitRequest,
    ExamSubmitResponse,
)
from app.services.training_service import TrainingService

router = APIRouter()

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".txt",
    ".md",
}

DOCUMENT_CONTENT_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
]

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".m4v",
}

VIDEO_CONTENT_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
]


def _question_to_public(question) -> ExamQuestionPublic:
    options = []
    if question.options:
        try:
            options = json.loads(question.options)
        except json.JSONDecodeError:
            options = []
    return ExamQuestionPublic(
        id=question.id,
        category_id=question.category_id,
        question=question.question,
        options=options,
        score=question.score,
        type=question.type,
    )


def _question_to_response(question) -> ExamQuestionResponse:
    options = []
    if question.options:
        try:
            options = json.loads(question.options)
        except json.JSONDecodeError:
            options = []
    answer = None
    if question.answer:
        try:
            answer = json.loads(question.answer)
        except json.JSONDecodeError:
            answer = question.answer
    return ExamQuestionResponse(
        id=question.id,
        category_id=question.category_id,
        question=question.question,
        options=options,
        answer=answer,
        score=question.score,
        type=question.type,
    )


@router.get("/categories", response_model=List[TrainingCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    return await TrainingService.list_categories(db)


@router.post("/categories", response_model=TrainingCategoryResponse)
async def create_category(
    payload: TrainingCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    return await TrainingService.create_category(db, payload)


@router.put("/categories/{category_id}", response_model=TrainingCategoryResponse)
async def update_category(
    category_id: int,
    payload: TrainingCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    category = await TrainingService.update_category(db, category_id, payload)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/categories/{category_id}", response_model=bool)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage categories")
    success = await TrainingService.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return True


@router.get("/overview", response_model=TrainingOverviewResponse)
async def get_overview(
    include_unpublished: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        include_unpublished = False
    return await TrainingService.build_overview(
        db,
        project_id=project_ctx.project_id,
        user_id=current_user.id,
        include_unpublished=include_unpublished,
    )


@router.get("/courses", response_model=List[TrainingCourseResponse])
async def list_courses(
    include_unpublished: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        include_unpublished = False
    return await TrainingService.list_courses(
        db,
        project_id=project_ctx.project_id,
        include_unpublished=include_unpublished,
    )


@router.post("/courses", response_model=TrainingCourseResponse)
async def create_course(
    payload: TrainingCourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage courses",
        )
    return await TrainingService.create_course(db, payload, project_ctx.project_id)


@router.put("/courses/{course_id}", response_model=TrainingCourseResponse)
async def update_course(
    course_id: int,
    payload: TrainingCourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage courses",
        )
    course = await TrainingService.update_course(
        db,
        course_id,
        payload,
        project_ctx.project_id,
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.delete("/courses/{course_id}", response_model=bool)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage courses",
        )
    success = await TrainingService.delete_course(db, course_id, project_ctx.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Course not found")
    return True


@router.get("/chapters", response_model=List[TrainingChapterResponse])
async def list_chapters(
    course_id: Optional[int] = Query(None),
    include_unpublished: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        include_unpublished = False
    return await TrainingService.list_chapters(
        db,
        project_id=project_ctx.project_id,
        course_id=course_id,
        include_unpublished=include_unpublished,
    )


@router.post("/chapters", response_model=TrainingChapterResponse)
async def create_chapter(
    payload: TrainingChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage chapters",
        )
    try:
        return await TrainingService.create_chapter(db, payload, project_ctx.project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/chapters/{chapter_id}", response_model=TrainingChapterResponse)
async def update_chapter(
    chapter_id: int,
    payload: TrainingChapterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage chapters",
        )
    try:
        chapter = await TrainingService.update_chapter(
            db,
            chapter_id,
            payload,
            project_ctx.project_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.delete("/chapters/{chapter_id}", response_model=bool)
async def delete_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can manage chapters",
        )
    success = await TrainingService.delete_chapter(
        db,
        chapter_id,
        project_ctx.project_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return True


@router.get("/contents", response_model=List[TrainingContentResponse])
async def list_contents(
    include_unpublished: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        include_unpublished = False
    return await TrainingService.list_contents(
        db,
        project_id=project_ctx.project_id,
        include_unpublished=include_unpublished,
    )


@router.get("/contents/{content_id}", response_model=TrainingContentResponse)
async def get_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    content = await TrainingService.get_content(db, content_id, project_ctx.project_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if (not current_user.is_staff) and (not content.published):
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/contents", response_model=TrainingContentResponse)
async def create_content(
    payload: TrainingContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage content")
    try:
        return await TrainingService.create_content(db, payload, project_ctx.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/contents/{content_id}", response_model=TrainingContentResponse)
async def update_content(
    content_id: int,
    payload: TrainingContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage content")
    try:
        content = await TrainingService.update_content(
            db,
            content_id,
            payload,
            project_ctx.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.delete("/contents/{content_id}", response_model=bool)
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage content")
    content = await TrainingService.get_content(db, content_id, project_ctx.project_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    success = await TrainingService.delete_content(db, content_id, project_ctx.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Content not found")
    remove_media_file(content.file_url)
    return True


@router.post("/contents/{content_id}/file", response_model=TrainingContentResponse)
async def upload_content_file(
    content_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can upload training files",
        )

    content = await TrainingService.get_content(db, content_id, project_ctx.project_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.content_type == "link":
        raise HTTPException(status_code=400, detail="Link content does not accept file upload")

    suffix = Path(file.filename or "").suffix.lower()
    if content.content_type == "document":
        if suffix not in DOCUMENT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="仅支持 PDF、Word、PPT、Excel、TXT、Markdown 文档")
        _, url = await save_file_upload(
            "training",
            content.id,
            file,
            max_size_mb=settings.TRAINING_DOCUMENT_MAX_SIZE_MB,
            allowed_content_types=DOCUMENT_CONTENT_TYPES,
        )
    elif content.content_type == "video":
        if suffix not in VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail="仅支持 MP4、MOV、AVI、MKV、WEBM、M4V 视频")
        _, url = await save_file_upload(
            "training",
            content.id,
            file,
            max_size_mb=settings.TRAINING_VIDEO_MAX_SIZE_MB,
            allowed_content_types=VIDEO_CONTENT_TYPES,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    if content.file_url and content.file_url != url:
        remove_media_file(content.file_url)

    payload = TrainingContentUpdate(file_url=url)
    updated = await TrainingService.update_content(
        db,
        content_id,
        payload,
        project_ctx.project_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")
    return updated


@router.get("/records", response_model=List[TrainingRecordResponse])
async def list_records(
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        user_id = current_user.id
    return await TrainingService.list_records(
        db,
        project_id=project_ctx.project_id,
        user_id=user_id,
    )


@router.post("/records", response_model=TrainingRecordResponse)
async def mark_record(
    payload: TrainingRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    try:
        return await TrainingService.mark_record(
            db,
            current_user.id,
            payload,
            project_ctx.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/questions", response_model=List[ExamQuestionResponse])
async def list_questions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can view questions")
    questions = await TrainingService.list_questions(db, project_ctx.project_id)
    return [_question_to_response(q) for q in questions]


@router.post("/questions", response_model=ExamQuestionResponse)
async def create_question(
    payload: ExamQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage questions")
    question = await TrainingService.create_question(db, payload, project_ctx.project_id)
    return _question_to_response(question)


@router.put("/questions/{question_id}", response_model=ExamQuestionResponse)
async def update_question(
    question_id: int,
    payload: ExamQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage questions")
    question = await TrainingService.update_question(db, question_id, payload, project_ctx.project_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return _question_to_response(question)


@router.delete("/questions/{question_id}", response_model=bool)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage questions")
    success = await TrainingService.delete_question(db, question_id, project_ctx.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return True


@router.get("/rules", response_model=List[ExamRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can view rules")
    return await TrainingService.list_rules(db, project_ctx.project_id)


@router.post("/rules", response_model=ExamRuleResponse)
async def create_rule(
    payload: ExamRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage rules")
    return await TrainingService.create_rule(db, payload, project_ctx.project_id)


@router.put("/rules/{rule_id}", response_model=ExamRuleResponse)
async def update_rule(
    rule_id: int,
    payload: ExamRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage rules")
    rule = await TrainingService.update_rule(db, rule_id, payload, project_ctx.project_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}", response_model=bool)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can manage rules")
    success = await TrainingService.delete_rule(db, rule_id, project_ctx.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return True


@router.post("/exam/start", response_model=ExamStartResponse)
async def start_exam(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    try:
        attempt, questions, rule = await TrainingService.start_exam(
            db,
            current_user.id,
            project_ctx.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    remaining_minutes = None
    if attempt.started_at:
        elapsed = datetime.utcnow() - attempt.started_at
        remaining_minutes = max(0, rule.duration_minutes - int(elapsed.total_seconds() // 60))
    return ExamStartResponse(
        attempt_id=attempt.id,
        questions=[_question_to_public(q) for q in questions],
        pass_score=rule.pass_score,
        duration_minutes=rule.duration_minutes,
        remaining_minutes=remaining_minutes,
        started_at=attempt.started_at,
    )


@router.post("/exam/{attempt_id}/submit", response_model=ExamSubmitResponse)
async def submit_exam(
    attempt_id: int,
    payload: ExamSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    attempt = await TrainingService.get_attempt(db, attempt_id, project_ctx.project_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Exam attempt not found")

    if attempt.user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit this attempt")

    try:
        attempt = await TrainingService.submit_exam(db, attempt, payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if attempt.passed:
        current_user.is_verified = True
        await db.commit()

    return ExamSubmitResponse(
        attempt_id=attempt.id,
        score=attempt.score,
        passed=attempt.passed,
    )
