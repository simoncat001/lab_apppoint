"""
Exam / paper / grading service.

核心职责：
1. 题库/题目/试卷的 CRUD 辅助（复杂组装放这里，避免 endpoint 膨胀）
2. 随机组卷：按 exam_paper_rule 从题库抽题（按题型/难度/知识点过滤）
3. 开考：把抽到或手选的题目落到 exam_answer_item 作为快照
4. 自动评分：客观题立即判分；主观题留给人工批改
5. 最终定分：所有题判完后计算总分、是否及格、更新 ExamAttempt

题目作答字段约定（answer 列存 JSON 文本）：
- single     : int     选项索引
- multi      : int[]   选项索引数组
- truefalse  : bool
- fill       : str     考生填写文本
- essay      : str     主观题答案，人工批改
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any, Iterable, List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import (
    ExamAnswerItem,
    ExamPaper,
    ExamPaperQuestion,
    ExamPaperRule,
    QuestionBank,
)
from app.models.training import ExamAttempt, ExamQuestion


# ==================== Paper composition ====================


def _effective_score(paper_q: ExamPaperQuestion) -> int:
    """手动组卷时每题最终分值：score_override 优先，否则用 question.score。"""
    if paper_q.score_override is not None:
        return paper_q.score_override
    return paper_q.question.score if paper_q.question else 0


async def compute_paper_total_score(db: AsyncSession, paper: ExamPaper) -> int:
    """根据当前组卷方式计算 total_score 预期值（持久化到 paper.total_score）。"""
    if paper.compose_type == "manual":
        q_rows = await db.execute(
            select(ExamPaperQuestion).where(ExamPaperQuestion.paper_id == paper.id)
        )
        total = 0
        for pq in q_rows.scalars().all():
            if pq.score_override is not None:
                total += pq.score_override
            else:
                q_row = await db.execute(
                    select(ExamQuestion).where(ExamQuestion.id == pq.question_id)
                )
                q = q_row.scalar_one_or_none()
                total += q.score if q else 0
        return total

    # random: total = sum(count * score_per_question)
    rules_rows = await db.execute(
        select(ExamPaperRule).where(ExamPaperRule.paper_id == paper.id)
    )
    return sum(r.count * r.score_per_question for r in rules_rows.scalars().all())


async def _query_candidate_question_ids(
    db: AsyncSession,
    *,
    project_id: Optional[int],
    bank_id: Optional[int],
    question_type: Optional[str],
    difficulty_min: int,
    difficulty_max: int,
    knowledge_point: Optional[str],
) -> List[int]:
    """按规则过滤候选题 id 池。project_id 用作多租户隔离。"""
    stmt = select(ExamQuestion.id).where(
        and_(
            ExamQuestion.difficulty >= difficulty_min,
            ExamQuestion.difficulty <= difficulty_max,
        )
    )
    if project_id is not None:
        # 允许全局题（project_id IS NULL）也被当前项目取用
        stmt = stmt.where(
            (ExamQuestion.project_id == project_id) | (ExamQuestion.project_id.is_(None))
        )
    if bank_id is not None:
        stmt = stmt.where(ExamQuestion.bank_id == bank_id)
    if question_type:
        stmt = stmt.where(ExamQuestion.type == question_type)
    if knowledge_point:
        stmt = stmt.where(ExamQuestion.knowledge_point == knowledge_point)
    rows = await db.execute(stmt)
    return [r[0] for r in rows.all()]


async def generate_questions_for_paper(
    db: AsyncSession, paper: ExamPaper
) -> List[Tuple[ExamQuestion, int]]:
    """
    返回最终的题目序列及每题分值。

    - manual：按 ExamPaperQuestion.sort_order
    - random：按每条 ExamPaperRule 抽 count 道，分值用 rule.score_per_question
    抽不够时按现有池子上限抽取（不报错），但返回值会带警告样的空提示由 endpoint 决定。
    """
    result: List[Tuple[ExamQuestion, int]] = []

    if paper.compose_type == "manual":
        rows = await db.execute(
            select(ExamPaperQuestion)
            .where(ExamPaperQuestion.paper_id == paper.id)
            .order_by(ExamPaperQuestion.sort_order, ExamPaperQuestion.id)
        )
        for pq in rows.scalars().all():
            q_row = await db.execute(
                select(ExamQuestion).where(ExamQuestion.id == pq.question_id)
            )
            q = q_row.scalar_one_or_none()
            if q is None:
                continue
            score = pq.score_override if pq.score_override is not None else q.score
            result.append((q, score))
        return result

    # random
    rules_rows = await db.execute(
        select(ExamPaperRule)
        .where(ExamPaperRule.paper_id == paper.id)
        .order_by(ExamPaperRule.id)
    )
    rules = list(rules_rows.scalars().all())
    picked_ids: set[int] = set()

    for rule in rules:
        pool = await _query_candidate_question_ids(
            db,
            project_id=paper.project_id,
            bank_id=rule.bank_id,
            question_type=rule.question_type,
            difficulty_min=rule.difficulty_min,
            difficulty_max=rule.difficulty_max,
            knowledge_point=rule.knowledge_point,
        )
        # 去重：同一份试卷同一题不重复
        pool = [qid for qid in pool if qid not in picked_ids]
        take = min(rule.count, len(pool))
        if take <= 0:
            continue
        picks = random.sample(pool, take)
        picked_ids.update(picks)
        q_rows = await db.execute(
            select(ExamQuestion).where(ExamQuestion.id.in_(picks))
        )
        # 保持与 picks 顺序一致
        by_id = {q.id: q for q in q_rows.scalars().all()}
        for qid in picks:
            q = by_id.get(qid)
            if q is not None:
                result.append((q, rule.score_per_question))

    return result


# ==================== Attempt lifecycle ====================


async def start_attempt(
    db: AsyncSession,
    *,
    paper: ExamPaper,
    user_id: int,
) -> Tuple[ExamAttempt, List[Tuple[ExamQuestion, int]]]:
    """
    新建 ExamAttempt 并把快照写入 exam_answer_item。
    返回 (attempt, [(question, score), ...])。
    """
    if not paper.published:
        raise ValueError("Paper is not published")

    picks = await generate_questions_for_paper(db, paper)
    if not picks:
        raise ValueError("No questions available for this paper")

    total_score = sum(score for _, score in picks)

    attempt = ExamAttempt(
        user_id=user_id,
        project_id=paper.project_id,
        paper_id=paper.id,
        started_at=datetime.utcnow(),
        score=0,
        total_score=total_score,
        passed=False,
        manual_graded=False,
        question_ids=json.dumps([q.id for q, _ in picks]),
    )
    db.add(attempt)
    await db.flush()

    for q, score in picks:
        db.add(
            ExamAnswerItem(
                attempt_id=attempt.id,
                question_id=q.id,
                full_score=score,
                answer=None,
                auto_score=None,
                manual_score=None,
                final_score=None,
            )
        )

    await db.commit()
    await db.refresh(attempt)
    return attempt, picks


# ==================== Auto grading ====================


def _parse_answer(raw: Optional[str]) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _auto_grade_item(question: ExamQuestion, submitted: Any, full_score: int) -> Optional[int]:
    """
    返回客观题自动判分；主观题（fill/essay）返回 None 等待人工批改。
    - single     : 精确匹配整数选项索引
    - multi      : 集合相等（忽略顺序）
    - truefalse  : bool 精确匹配
    - fill       : 严格匹配 question.answer（去首尾空白、忽略大小写），否则留给人工
    - essay      : 始终人工批改
    规则设计保守：不做部分给分，答对得 full_score，答错得 0。
    """
    correct = _parse_answer(question.answer)
    qtype = question.type

    if qtype == "single":
        if submitted is None:
            return 0
        try:
            return full_score if int(submitted) == int(correct) else 0
        except (TypeError, ValueError):
            return 0

    if qtype == "multi":
        if not isinstance(submitted, list) or not isinstance(correct, list):
            return 0
        try:
            return full_score if set(int(x) for x in submitted) == set(int(x) for x in correct) else 0
        except (TypeError, ValueError):
            return 0

    if qtype == "truefalse":
        if submitted is None:
            return 0
        return full_score if bool(submitted) == bool(correct) else 0

    if qtype == "fill":
        # 允许 question.answer 为字符串或字符串数组（任意一个匹配即可）
        if submitted is None:
            return 0
        sub_norm = str(submitted).strip().casefold()
        expected_list: List[str] = []
        if isinstance(correct, list):
            expected_list = [str(x).strip().casefold() for x in correct]
        elif correct is not None:
            expected_list = [str(correct).strip().casefold()]
        if not expected_list:
            return None  # 无参考答案 → 交给人工
        return full_score if sub_norm in expected_list else 0

    if qtype == "essay":
        return None

    # 未知题型：走人工
    return None


async def submit_attempt(
    db: AsyncSession,
    *,
    attempt: ExamAttempt,
    answers_by_qid: dict[int, Any],
) -> ExamAttempt:
    """考生提交：写入每题 answer + 立即计算客观题自动分。最终得分在所有人工批改完成后再算。"""
    if attempt.completed_at is not None:
        raise ValueError("Attempt already submitted")

    item_rows = await db.execute(
        select(ExamAnswerItem).where(ExamAnswerItem.attempt_id == attempt.id)
    )
    items = list(item_rows.scalars().all())

    paper = await db.get(ExamPaper, attempt.paper_id) if attempt.paper_id else None
    if (
        paper is not None
        and attempt.started_at is not None
        and datetime.utcnow() > attempt.started_at + timedelta(minutes=paper.duration_minutes)
    ):
        now = datetime.utcnow()
        for item in items:
            item.answer = None
            item.auto_score = 0
            item.final_score = 0
            item.graded_at = now
        attempt.completed_at = now
        attempt.score = 0
        attempt.passed = False
        attempt.manual_graded = True
        await db.commit()
        await db.refresh(attempt)
        return attempt

    # 预加载题目
    q_rows = await db.execute(
        select(ExamQuestion).where(
            ExamQuestion.id.in_([it.question_id for it in items])
        )
    )
    q_by_id = {q.id: q for q in q_rows.scalars().all()}

    for item in items:
        question = q_by_id.get(item.question_id)
        if question is None:
            continue
        submitted = answers_by_qid.get(item.question_id)
        item.answer = json.dumps(submitted) if submitted is not None else None
        auto = _auto_grade_item(question, submitted, item.full_score)
        item.auto_score = auto
        if auto is not None:
            # 客观题：最终分直接定
            item.final_score = auto
            item.graded_at = datetime.utcnow()

    attempt.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(attempt)

    # 所有题都已定分（无 essay/未给参考答案的 fill）→ 直接 finalize
    await _maybe_finalize(db, attempt)
    return attempt


async def grade_item(
    db: AsyncSession,
    *,
    item: ExamAnswerItem,
    manual_score: int,
    grader_id: int,
    comment: Optional[str] = None,
) -> ExamAnswerItem:
    """人工阅卷单题。"""
    if manual_score < 0 or manual_score > item.full_score:
        raise ValueError("manual_score out of range")
    item.manual_score = manual_score
    item.final_score = manual_score
    item.grader_id = grader_id
    item.graded_at = datetime.utcnow()
    if comment is not None:
        item.comment = comment
    await db.commit()
    await db.refresh(item)

    attempt = await db.get(ExamAttempt, item.attempt_id)
    if attempt is not None:
        await _maybe_finalize(db, attempt)
    return item


async def _maybe_finalize(db: AsyncSession, attempt: ExamAttempt) -> None:
    """若无待批改题，则汇总最终分并更新 passed/manual_graded。"""
    rows = await db.execute(
        select(func.count())
        .select_from(ExamAnswerItem)
        .where(
            and_(
                ExamAnswerItem.attempt_id == attempt.id,
                ExamAnswerItem.final_score.is_(None),
            )
        )
    )
    pending = int(rows.scalar() or 0)
    if pending > 0:
        if attempt.manual_graded:
            attempt.manual_graded = False
            await db.commit()
        return

    sum_row = await db.execute(
        select(func.coalesce(func.sum(ExamAnswerItem.final_score), 0)).where(
            ExamAnswerItem.attempt_id == attempt.id
        )
    )
    total = int(sum_row.scalar() or 0)
    attempt.score = total
    attempt.manual_graded = True

    paper = await db.get(ExamPaper, attempt.paper_id) if attempt.paper_id else None
    pass_score = paper.pass_score if paper else 60
    attempt.passed = total >= pass_score
    await db.commit()


# ==================== Stats ====================


async def paper_stats(db: AsyncSession, paper_id: int) -> dict:
    rows = await db.execute(
        select(
            func.count(),
            func.coalesce(func.avg(ExamAttempt.score), 0),
            func.coalesce(func.max(ExamAttempt.score), 0),
            func.coalesce(func.min(ExamAttempt.score), 0),
            func.coalesce(
                func.sum(case((ExamAttempt.passed == True, 1), else_=0)), 0
            ),
        ).where(
            and_(
                ExamAttempt.paper_id == paper_id,
                ExamAttempt.completed_at.is_not(None),
            )
        )
    )
    row = rows.one()
    count, avg, mx, mn, passed = row
    count_i = int(count or 0)
    passed_i = int(passed or 0)
    return {
        "paper_id": paper_id,
        "attempt_count": count_i,
        "pass_count": passed_i,
        "pass_rate": (passed_i / count_i) if count_i else 0.0,
        "avg_score": float(avg or 0),
        "max_score": int(mx or 0),
        "min_score": int(mn or 0),
    }


# ==================== Helpers used by endpoints ====================


async def ensure_bank_in_project(
    db: AsyncSession, bank_id: int, project_id: Optional[int]
) -> QuestionBank:
    bank = await db.get(QuestionBank, bank_id)
    if bank is None:
        raise ValueError("Question bank not found")
    if project_id is not None and bank.project_id not in (None, project_id):
        raise ValueError("Question bank is not in current project")
    return bank


async def ensure_paper_in_project(
    db: AsyncSession, paper_id: int, project_id: Optional[int]
) -> ExamPaper:
    paper = await db.get(ExamPaper, paper_id)
    if paper is None:
        raise ValueError("Paper not found")
    if project_id is not None and paper.project_id not in (None, project_id):
        raise ValueError("Paper is not in current project")
    return paper


async def iter_bank_question_counts(
    db: AsyncSession, bank_ids: Iterable[int]
) -> dict[int, int]:
    ids = list(bank_ids)
    if not ids:
        return {}
    rows = await db.execute(
        select(ExamQuestion.bank_id, func.count())
        .where(ExamQuestion.bank_id.in_(ids))
        .group_by(ExamQuestion.bank_id)
    )
    return {bid: int(cnt) for bid, cnt in rows.all()}
