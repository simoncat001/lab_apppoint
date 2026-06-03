"""
/api/exams endpoints.

覆盖：
- 题库 CRUD
- 题目（富字段）CRUD
- 试卷 CRUD（含手动题单 / 随机规则 / 预览 / 发布切换）
- 开考 / 提交
- 考试记录查询 / 阅卷 / 统计
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.db.session import get_db
from app.models.exam import (
    ExamAnswerItem,
    ExamPaper,
    ExamPaperQuestion,
    ExamPaperRule,
    QuestionBank,
)
from app.models.training import ExamAttempt, ExamQuestion
from app.models.user import User
from app.schemas.exam import (
    AttemptAnswerItemResponse,
    ExamAttemptDetail,
    ExamAttemptSummary,
    ExamPaperCreate,
    ExamPaperDetailResponse,
    ExamPaperResponse,
    ExamPaperUpdate,
    ExamQuestionPublic,
    ExamQuestionRich,
    ExamQuestionRichCreate,
    ExamQuestionRichUpdate,
    ExamStartPaperResponse,
    ExamSubmitPaperRequest,
    GradeBatchRequest,
    GradeItemRequest,
    PaperPreviewResponse,
    PaperQuestionItem,
    PaperQuestionResponse,
    PaperRuleItem,
    PaperRuleResponse,
    PaperStatsResponse,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionBankUpdate,
)
from app.services import exam_service

router = APIRouter()


# ==================== 工具函数 ====================


def _staff_only(user: User) -> None:
    if not (user.is_staff or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff only")


def _ensure_attempt_in_current_project(
    attempt: ExamAttempt,
    project_ctx: CurrentProjectContext,
) -> None:
    if int(getattr(attempt, "project_id", 0) or 0) != int(project_ctx.project_id):
        raise HTTPException(status_code=404, detail="Attempt not found")


async def _get_attempt_in_current_project(
    db: AsyncSession,
    attempt_id: int,
    project_ctx: CurrentProjectContext,
) -> ExamAttempt:
    attempt = await db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    _ensure_attempt_in_current_project(attempt, project_ctx)
    return attempt


async def _get_answer_item_in_current_project(
    db: AsyncSession,
    item_id: int,
    project_ctx: CurrentProjectContext,
) -> ExamAnswerItem:
    item = await db.get(ExamAnswerItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Answer item not found")
    await _get_attempt_in_current_project(db, item.attempt_id, project_ctx)
    return item


def _loads(raw: Optional[str], default: Any = None) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _question_to_rich(q: ExamQuestion) -> ExamQuestionRich:
    return ExamQuestionRich(
        id=q.id,
        project_id=q.project_id,
        bank_id=q.bank_id,
        category_id=q.category_id,
        question=q.question,
        type=q.type,
        options=_loads(q.options, []),
        answer=_loads(q.answer, None),
        score=q.score,
        difficulty=q.difficulty,
        knowledge_point=q.knowledge_point,
        analysis=q.analysis,
    )


def _question_to_public(q: ExamQuestion, score: int) -> ExamQuestionPublic:
    return ExamQuestionPublic(
        id=q.id,
        question=q.question,
        type=q.type,
        options=_loads(q.options, []),
        score=score,
    )


# ==================== 题库 CRUD ====================


@router.get("/banks", response_model=List[QuestionBankResponse])
async def list_banks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    stmt = select(QuestionBank)
    if project_ctx.project_id is not None:
        stmt = stmt.where(
            (QuestionBank.project_id == project_ctx.project_id)
            | (QuestionBank.project_id.is_(None))
        )
    rows = await db.execute(stmt.order_by(QuestionBank.id.desc()))
    banks = list(rows.scalars().all())
    counts = await exam_service.iter_bank_question_counts(db, [b.id for b in banks])
    result = []
    for b in banks:
        payload = QuestionBankResponse.model_validate(b)
        payload.question_count = counts.get(b.id, 0)
        result.append(payload)
    return result


@router.post("/banks", response_model=QuestionBankResponse)
async def create_bank(
    payload: QuestionBankCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    bank = QuestionBank(
        name=payload.name,
        description=payload.description,
        project_id=project_ctx.project_id,
    )
    db.add(bank)
    await db.commit()
    await db.refresh(bank)
    resp = QuestionBankResponse.model_validate(bank)
    resp.question_count = 0
    return resp


@router.put("/banks/{bank_id}", response_model=QuestionBankResponse)
async def update_bank(
    bank_id: int,
    payload: QuestionBankUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    try:
        bank = await exam_service.ensure_bank_in_project(
            db, bank_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(bank, k, v)
    await db.commit()
    await db.refresh(bank)
    counts = await exam_service.iter_bank_question_counts(db, [bank.id])
    resp = QuestionBankResponse.model_validate(bank)
    resp.question_count = counts.get(bank.id, 0)
    return resp


@router.delete("/banks/{bank_id}", response_model=bool)
async def delete_bank(
    bank_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    try:
        bank = await exam_service.ensure_bank_in_project(
            db, bank_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.delete(bank)
    await db.commit()
    return True


# ==================== 题目 CRUD（富字段版） ====================


@router.get("/questions", response_model=List[ExamQuestionRich])
async def list_questions_rich(
    bank_id: Optional[int] = Query(None),
    question_type: Optional[str] = Query(None),
    difficulty: Optional[int] = Query(None, ge=1, le=5),
    keyword: Optional[str] = Query(None, description="按题干模糊搜索"),
    knowledge_point: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    stmt = select(ExamQuestion)
    if project_ctx.project_id is not None:
        stmt = stmt.where(
            (ExamQuestion.project_id == project_ctx.project_id)
            | (ExamQuestion.project_id.is_(None))
        )
    if bank_id is not None:
        stmt = stmt.where(ExamQuestion.bank_id == bank_id)
    if question_type:
        stmt = stmt.where(ExamQuestion.type == question_type)
    if difficulty is not None:
        stmt = stmt.where(ExamQuestion.difficulty == difficulty)
    if knowledge_point:
        stmt = stmt.where(ExamQuestion.knowledge_point == knowledge_point)
    if keyword:
        stmt = stmt.where(ExamQuestion.question.ilike(f"%{keyword}%"))
    rows = await db.execute(stmt.order_by(ExamQuestion.id.desc()))
    return [_question_to_rich(q) for q in rows.scalars().all()]


@router.post("/questions", response_model=ExamQuestionRich)
async def create_question_rich(
    payload: ExamQuestionRichCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    q = ExamQuestion(
        project_id=project_ctx.project_id,
        bank_id=payload.bank_id,
        category_id=payload.category_id,
        question=payload.question,
        type=payload.type,
        options=json.dumps(payload.options) if payload.options is not None else None,
        answer=json.dumps(payload.answer) if payload.answer is not None else "",
        score=payload.score,
        difficulty=payload.difficulty,
        knowledge_point=payload.knowledge_point,
        analysis=payload.analysis,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return _question_to_rich(q)


@router.put("/questions/{question_id}", response_model=ExamQuestionRich)
async def update_question_rich(
    question_id: int,
    payload: ExamQuestionRichUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    q = await db.get(ExamQuestion, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if (
        project_ctx.project_id is not None
        and q.project_id is not None
        and q.project_id != project_ctx.project_id
    ):
        raise HTTPException(status_code=404, detail="Question not in current project")

    data = payload.model_dump(exclude_unset=True)
    if "options" in data:
        q.options = json.dumps(data.pop("options")) if data.get("options") is not None else None
    if "answer" in data:
        q.answer = json.dumps(data.pop("answer")) if data.get("answer") is not None else ""
    for k, v in data.items():
        setattr(q, k, v)
    await db.commit()
    await db.refresh(q)
    return _question_to_rich(q)


@router.delete("/questions/{question_id}", response_model=bool)
async def delete_question_rich(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    q = await db.get(ExamQuestion, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if (
        project_ctx.project_id is not None
        and q.project_id is not None
        and q.project_id != project_ctx.project_id
    ):
        raise HTTPException(status_code=404, detail="Question not in current project")
    await db.delete(q)
    await db.commit()
    return True


# ==================== 试卷 CRUD ====================


async def _paper_question_count(db: AsyncSession, paper: ExamPaper) -> int:
    if paper.compose_type == "manual":
        row = await db.execute(
            select(func.count()).select_from(ExamPaperQuestion).where(
                ExamPaperQuestion.paper_id == paper.id
            )
        )
        return int(row.scalar() or 0)
    row = await db.execute(
        select(func.coalesce(func.sum(ExamPaperRule.count), 0)).where(
            ExamPaperRule.paper_id == paper.id
        )
    )
    return int(row.scalar() or 0)


async def _paper_to_response(db: AsyncSession, paper: ExamPaper) -> ExamPaperResponse:
    resp = ExamPaperResponse.model_validate(paper)
    resp.question_count = await _paper_question_count(db, paper)
    return resp


async def _sync_paper_questions(
    db: AsyncSession, paper: ExamPaper, items: List[PaperQuestionItem]
) -> None:
    await db.execute(
        sa_delete(ExamPaperQuestion).where(ExamPaperQuestion.paper_id == paper.id)
    )
    for item in items:
        db.add(
            ExamPaperQuestion(
                paper_id=paper.id,
                question_id=item.question_id,
                sort_order=item.sort_order,
                score_override=item.score_override,
            )
        )


async def _sync_paper_rules(
    db: AsyncSession, paper: ExamPaper, rules: List[PaperRuleItem]
) -> None:
    await db.execute(
        sa_delete(ExamPaperRule).where(ExamPaperRule.paper_id == paper.id)
    )
    for r in rules:
        db.add(
            ExamPaperRule(
                paper_id=paper.id,
                bank_id=r.bank_id,
                question_type=r.question_type,
                difficulty_min=r.difficulty_min,
                difficulty_max=r.difficulty_max,
                count=r.count,
                score_per_question=r.score_per_question,
                knowledge_point=r.knowledge_point,
            )
        )


@router.get("/papers", response_model=List[ExamPaperResponse])
async def list_papers(
    published_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    stmt = select(ExamPaper)
    if project_ctx.project_id is not None:
        stmt = stmt.where(
            (ExamPaper.project_id == project_ctx.project_id)
            | (ExamPaper.project_id.is_(None))
        )
    # 非 staff 只能看已发布
    if not (current_user.is_staff or current_user.is_superuser):
        stmt = stmt.where(ExamPaper.published.is_(True))
    elif published_only:
        stmt = stmt.where(ExamPaper.published.is_(True))
    rows = await db.execute(stmt.order_by(ExamPaper.id.desc()))
    papers = list(rows.scalars().all())
    result = []
    for p in papers:
        result.append(await _paper_to_response(db, p))
    return result


@router.post("/papers", response_model=ExamPaperDetailResponse)
async def create_paper(
    payload: ExamPaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    paper = ExamPaper(
        project_id=project_ctx.project_id,
        name=payload.name,
        description=payload.description,
        compose_type=payload.compose_type,
        total_score=payload.total_score,
        pass_score=payload.pass_score,
        duration_minutes=payload.duration_minutes,
        show_result_immediately=payload.show_result_immediately,
        published=payload.published,
        created_by=current_user.id,
    )
    db.add(paper)
    await db.flush()

    if payload.questions:
        await _sync_paper_questions(db, paper, payload.questions)
    if payload.rules:
        await _sync_paper_rules(db, paper, payload.rules)

    # 若未显式提供 total_score，自动按组成方式计算
    if not payload.total_score:
        paper.total_score = await exam_service.compute_paper_total_score(db, paper)

    await db.commit()
    await db.refresh(paper)
    return await _load_paper_detail(db, paper)


@router.get("/papers/{paper_id}", response_model=ExamPaperDetailResponse)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    try:
        paper = await exam_service.ensure_paper_in_project(
            db, paper_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not (current_user.is_staff or current_user.is_superuser) and not paper.published:
        raise HTTPException(status_code=404, detail="Paper not found")
    return await _load_paper_detail(db, paper)


async def _load_paper_detail(db: AsyncSession, paper: ExamPaper) -> ExamPaperDetailResponse:
    # questions
    pq_rows = await db.execute(
        select(ExamPaperQuestion)
        .where(ExamPaperQuestion.paper_id == paper.id)
        .order_by(ExamPaperQuestion.sort_order, ExamPaperQuestion.id)
    )
    pqs = list(pq_rows.scalars().all())
    q_rows = await db.execute(
        select(ExamQuestion).where(
            ExamQuestion.id.in_([pq.question_id for pq in pqs] or [0])
        )
    )
    q_by_id = {q.id: q for q in q_rows.scalars().all()}
    question_items: List[PaperQuestionResponse] = []
    for pq in pqs:
        q = q_by_id.get(pq.question_id)
        question_items.append(
            PaperQuestionResponse(
                id=pq.id,
                paper_id=pq.paper_id,
                question_id=pq.question_id,
                sort_order=pq.sort_order,
                score_override=pq.score_override,
                question=_question_to_rich(q) if q else None,
            )
        )

    # rules
    rule_rows = await db.execute(
        select(ExamPaperRule).where(ExamPaperRule.paper_id == paper.id)
    )
    rules = [PaperRuleResponse.model_validate(r) for r in rule_rows.scalars().all()]

    base = await _paper_to_response(db, paper)
    return ExamPaperDetailResponse(
        **base.model_dump(),
        questions=question_items,
        rules=rules,
    )


@router.put("/papers/{paper_id}", response_model=ExamPaperDetailResponse)
async def update_paper(
    paper_id: int,
    payload: ExamPaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    try:
        paper = await exam_service.ensure_paper_in_project(
            db, paper_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    data = payload.model_dump(exclude_unset=True)
    questions = data.pop("questions", None)
    rules = data.pop("rules", None)
    for k, v in data.items():
        setattr(paper, k, v)
    await db.flush()

    if questions is not None:
        await _sync_paper_questions(
            db, paper, [PaperQuestionItem.model_validate(i) for i in questions]
        )
    if rules is not None:
        await _sync_paper_rules(
            db, paper, [PaperRuleItem.model_validate(i) for i in rules]
        )

    if paper.total_score == 0:
        paper.total_score = await exam_service.compute_paper_total_score(db, paper)

    await db.commit()
    await db.refresh(paper)
    return await _load_paper_detail(db, paper)


@router.delete("/papers/{paper_id}", response_model=bool)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    try:
        paper = await exam_service.ensure_paper_in_project(
            db, paper_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.delete(paper)
    await db.commit()
    return True


@router.post("/papers/{paper_id}/preview", response_model=PaperPreviewResponse)
async def preview_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """管理员组卷预览：按当前 rules/questions 抽一次（不持久化）。"""
    _staff_only(current_user)
    try:
        paper = await exam_service.ensure_paper_in_project(
            db, paper_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    picks = await exam_service.generate_questions_for_paper(db, paper)
    return PaperPreviewResponse(
        questions=[_question_to_rich(q) for q, _ in picks],
        total_score=sum(s for _, s in picks),
    )


# ==================== 开考 / 提交 ====================


@router.post("/papers/{paper_id}/start", response_model=ExamStartPaperResponse)
async def start_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    try:
        paper = await exam_service.ensure_paper_in_project(
            db, paper_id, project_ctx.project_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not paper.published and not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=404, detail="Paper not available")

    try:
        attempt, picks = await exam_service.start_attempt(
            db, paper=paper, user_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    elapsed_min = int((datetime.utcnow() - attempt.started_at).total_seconds() // 60)
    remaining = max(0, paper.duration_minutes - elapsed_min)
    return ExamStartPaperResponse(
        attempt_id=attempt.id,
        paper_id=paper.id,
        paper_name=paper.name,
        total_score=attempt.total_score,
        pass_score=paper.pass_score,
        duration_minutes=paper.duration_minutes,
        remaining_minutes=remaining,
        started_at=attempt.started_at,
        questions=[_question_to_public(q, s) for q, s in picks],
    )


@router.post("/attempts/{attempt_id}/submit", response_model=ExamAttemptSummary)
async def submit_paper(
    attempt_id: int,
    payload: ExamSubmitPaperRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    attempt = await _get_attempt_in_current_project(db, attempt_id, project_ctx)
    if attempt.user_id != current_user.id and not (
        current_user.is_staff or current_user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Not your attempt")

    answers_by_qid = {a.question_id: a.answer for a in payload.answers}
    try:
        attempt = await exam_service.submit_attempt(
            db, attempt=attempt, answers_by_qid=answers_by_qid
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExamAttemptSummary.model_validate(attempt)


# ==================== 考试记录 / 阅卷 ====================


@router.get("/attempts", response_model=List[ExamAttemptSummary])
async def list_attempts(
    paper_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    pending_grading: Optional[bool] = Query(
        None, description="仅列待批改（manual_graded=False 且 completed_at 非空）"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    stmt = select(ExamAttempt)
    # 非 staff 仅能查自己的
    if not (current_user.is_staff or current_user.is_superuser):
        stmt = stmt.where(ExamAttempt.user_id == current_user.id)
    elif user_id is not None:
        stmt = stmt.where(ExamAttempt.user_id == user_id)
    stmt = stmt.where(ExamAttempt.project_id == project_ctx.project_id)
    if paper_id is not None:
        stmt = stmt.where(ExamAttempt.paper_id == paper_id)
    if pending_grading:
        stmt = stmt.where(
            and_(
                ExamAttempt.completed_at.is_not(None),
                ExamAttempt.manual_graded.is_(False),
            )
        )
    rows = await db.execute(stmt.order_by(ExamAttempt.id.desc()))
    return [ExamAttemptSummary.model_validate(a) for a in rows.scalars().all()]


@router.get("/attempts/{attempt_id}", response_model=ExamAttemptDetail)
async def get_attempt_detail(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    attempt = await _get_attempt_in_current_project(db, attempt_id, project_ctx)
    is_staff = current_user.is_staff or current_user.is_superuser
    if attempt.user_id != current_user.id and not is_staff:
        raise HTTPException(status_code=403, detail="Not your attempt")

    item_rows = await db.execute(
        select(ExamAnswerItem).where(ExamAnswerItem.attempt_id == attempt.id)
    )
    items = list(item_rows.scalars().all())
    q_rows = await db.execute(
        select(ExamQuestion).where(
            ExamQuestion.id.in_([i.question_id for i in items] or [0])
        )
    )
    q_by_id = {q.id: q for q in q_rows.scalars().all()}

    paper = await db.get(ExamPaper, attempt.paper_id) if attempt.paper_id else None
    hide_answers = (
        not is_staff
        and paper is not None
        and not paper.show_result_immediately
        and not attempt.manual_graded
    )

    item_responses: List[AttemptAnswerItemResponse] = []
    for it in items:
        q = q_by_id.get(it.question_id)
        rich = _question_to_rich(q) if q else None
        if hide_answers and rich is not None:
            # 对学员：未允许立即展示 且 尚未全部批改 → 隐藏答案与解析
            rich.answer = None
            rich.analysis = None
        item_responses.append(
            AttemptAnswerItemResponse(
                id=it.id,
                attempt_id=it.attempt_id,
                question_id=it.question_id,
                full_score=it.full_score,
                answer=_loads(it.answer, None),
                auto_score=it.auto_score,
                manual_score=it.manual_score,
                final_score=it.final_score,
                grader_id=it.grader_id,
                graded_at=it.graded_at,
                comment=it.comment,
                question=rich,
            )
        )

    base = ExamAttemptSummary.model_validate(attempt)
    return ExamAttemptDetail(**base.model_dump(), items=item_responses)


@router.post("/attempts/items/{item_id}/grade", response_model=AttemptAnswerItemResponse)
async def grade_single_item(
    item_id: int,
    payload: GradeItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    item = await _get_answer_item_in_current_project(db, item_id, project_ctx)
    try:
        item = await exam_service.grade_item(
            db,
            item=item,
            manual_score=payload.manual_score,
            grader_id=current_user.id,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AttemptAnswerItemResponse(
        id=item.id,
        attempt_id=item.attempt_id,
        question_id=item.question_id,
        full_score=item.full_score,
        answer=_loads(item.answer, None),
        auto_score=item.auto_score,
        manual_score=item.manual_score,
        final_score=item.final_score,
        grader_id=item.grader_id,
        graded_at=item.graded_at,
        comment=item.comment,
    )


@router.post("/attempts/{attempt_id}/grade-batch", response_model=ExamAttemptSummary)
async def grade_batch(
    attempt_id: int,
    payload: GradeBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    attempt = await _get_attempt_in_current_project(db, attempt_id, project_ctx)

    item_rows = await db.execute(
        select(ExamAnswerItem).where(
            and_(
                ExamAnswerItem.attempt_id == attempt.id,
                ExamAnswerItem.id.in_([i.item_id for i in payload.items] or [0]),
            )
        )
    )
    items_by_id = {it.id: it for it in item_rows.scalars().all()}
    for entry in payload.items:
        item = items_by_id.get(entry.item_id)
        if item is None:
            continue
        try:
            await exam_service.grade_item(
                db,
                item=item,
                manual_score=entry.manual_score,
                grader_id=current_user.id,
                comment=entry.comment,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.refresh(attempt)
    return ExamAttemptSummary.model_validate(attempt)


# ==================== 统计 ====================


@router.get("/papers/{paper_id}/stats", response_model=PaperStatsResponse)
async def get_paper_stats(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    _staff_only(current_user)
    try:
        await exam_service.ensure_paper_in_project(db, paper_id, project_ctx.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    data = await exam_service.paper_stats(db, paper_id)
    return PaperStatsResponse(**data)
