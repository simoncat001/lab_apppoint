import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
from app.schemas.training import (
    TrainingCategoryCreate,
    TrainingCourseCreate,
    TrainingCourseDetailResponse,
    TrainingCourseUpdate,
    TrainingChapterCreate,
    TrainingChapterDetailResponse,
    TrainingChapterUpdate,
    TrainingContentCreate,
    TrainingContentProgressResponse,
    TrainingContentUpdate,
    TrainingOverviewResponse,
    TrainingRecordCreate,
    ExamQuestionCreate,
    ExamQuestionUpdate,
    ExamRuleCreate,
    ExamRuleUpdate,
)


def _project_filter(column, project_id: Optional[int]):
    if project_id is None:
        return column.is_(None)
    return column == project_id


def _progress_percent(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((completed / total) * 100, 2)


def _content_to_progress(
    content: TrainingContent, record_by_content_id: dict[int, TrainingRecord]
) -> TrainingContentProgressResponse:
    record = record_by_content_id.get(content.id)
    payload = TrainingContentProgressResponse.model_validate(content)
    payload.learned = record is not None
    payload.learned_at = record.completed_at if record else None
    return payload


class TrainingService:
    @staticmethod
    async def get_attempt(
        db: AsyncSession,
        attempt_id: int,
        project_id: int,
    ) -> Optional[ExamAttempt]:
        result = await db.execute(
            select(ExamAttempt).where(
                ExamAttempt.id == attempt_id,
                ExamAttempt.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_categories(db: AsyncSession) -> List[TrainingCategory]:
        result = await db.execute(
            select(TrainingCategory).order_by(TrainingCategory.name.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def create_category(
        db: AsyncSession, data: TrainingCategoryCreate
    ) -> TrainingCategory:
        category = TrainingCategory(name=data.name)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, data: TrainingCategoryCreate
    ) -> Optional[TrainingCategory]:
        result = await db.execute(
            select(TrainingCategory).where(TrainingCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            return None
        category.name = data.name
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int) -> bool:
        result = await db.execute(
            select(TrainingCategory).where(TrainingCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            return False
        await db.delete(category)
        await db.commit()
        return True

    @staticmethod
    async def list_courses(
        db: AsyncSession,
        project_id: int,
        include_unpublished: bool = False,
    ) -> List[TrainingCourse]:
        query = select(TrainingCourse).where(
            _project_filter(TrainingCourse.project_id, project_id)
        )
        if not include_unpublished:
            query = query.where(TrainingCourse.published.is_(True))
        result = await db.execute(
            query.order_by(TrainingCourse.sort_order.asc(), TrainingCourse.id.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_course(
        db: AsyncSession,
        course_id: int,
        project_id: int,
    ) -> Optional[TrainingCourse]:
        result = await db.execute(
            select(TrainingCourse).where(
                TrainingCourse.id == course_id,
                _project_filter(TrainingCourse.project_id, project_id),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_course(
        db: AsyncSession,
        data: TrainingCourseCreate,
        project_id: int,
    ) -> TrainingCourse:
        course = TrainingCourse(
            title=data.title,
            summary=data.summary,
            cover_url=data.cover_url,
            category_id=data.category_id,
            project_id=project_id,
            sort_order=data.sort_order,
            published=data.published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course

    @staticmethod
    async def update_course(
        db: AsyncSession,
        course_id: int,
        data: TrainingCourseUpdate,
        project_id: int,
    ) -> Optional[TrainingCourse]:
        course = await TrainingService.get_course(db, course_id, project_id)
        if not course:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)
        course.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(course)
        return course

    @staticmethod
    async def delete_course(db: AsyncSession, course_id: int, project_id: int) -> bool:
        course = await TrainingService.get_course(db, course_id, project_id)
        if not course:
            return False

        chapter_rows = await db.execute(
            select(TrainingChapter).where(TrainingChapter.course_id == course.id)
        )
        chapters = list(chapter_rows.scalars().all())
        chapter_ids = [chapter.id for chapter in chapters]

        if chapter_ids:
            content_rows = await db.execute(
                select(TrainingContent).where(TrainingContent.chapter_id.in_(chapter_ids))
            )
            for content in content_rows.scalars().all():
                content.chapter_id = None

            for chapter in chapters:
                await db.delete(chapter)

        await db.delete(course)
        await db.commit()
        return True

    @staticmethod
    async def list_chapters(
        db: AsyncSession,
        project_id: int,
        course_id: Optional[int] = None,
        include_unpublished: bool = False,
    ) -> List[TrainingChapter]:
        query = (
            select(TrainingChapter)
            .join(TrainingCourse, TrainingCourse.id == TrainingChapter.course_id)
            .where(_project_filter(TrainingCourse.project_id, project_id))
        )
        if course_id is not None:
            query = query.where(TrainingChapter.course_id == course_id)
        if not include_unpublished:
            query = query.where(
                TrainingChapter.published.is_(True),
                TrainingCourse.published.is_(True),
            )
        result = await db.execute(
            query.order_by(TrainingChapter.sort_order.asc(), TrainingChapter.id.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_chapter(
        db: AsyncSession,
        chapter_id: int,
        project_id: int,
    ) -> Optional[TrainingChapter]:
        result = await db.execute(
            select(TrainingChapter)
            .join(TrainingCourse, TrainingCourse.id == TrainingChapter.course_id)
            .where(
                TrainingChapter.id == chapter_id,
                _project_filter(TrainingCourse.project_id, project_id),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_chapter(
        db: AsyncSession,
        data: TrainingChapterCreate,
        project_id: int,
    ) -> TrainingChapter:
        course = await TrainingService.get_course(db, data.course_id, project_id)
        if not course:
            raise ValueError("Course not found in current project")

        chapter = TrainingChapter(
            course_id=data.course_id,
            title=data.title,
            summary=data.summary,
            sort_order=data.sort_order,
            published=data.published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
        return chapter

    @staticmethod
    async def update_chapter(
        db: AsyncSession,
        chapter_id: int,
        data: TrainingChapterUpdate,
        project_id: int,
    ) -> Optional[TrainingChapter]:
        chapter = await TrainingService.get_chapter(db, chapter_id, project_id)
        if not chapter:
            return None

        update_data = data.model_dump(exclude_unset=True)
        next_course_id = update_data.get("course_id")
        if next_course_id is not None:
            course = await TrainingService.get_course(db, next_course_id, project_id)
            if not course:
                raise ValueError("Course not found in current project")

        for field, value in update_data.items():
            setattr(chapter, field, value)
        chapter.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(chapter)
        return chapter

    @staticmethod
    async def delete_chapter(
        db: AsyncSession,
        chapter_id: int,
        project_id: int,
    ) -> bool:
        chapter = await TrainingService.get_chapter(db, chapter_id, project_id)
        if not chapter:
            return False

        content_rows = await db.execute(
            select(TrainingContent).where(TrainingContent.chapter_id == chapter.id)
        )
        for content in content_rows.scalars().all():
            content.chapter_id = None

        await db.delete(chapter)
        await db.commit()
        return True

    @staticmethod
    async def build_overview(
        db: AsyncSession,
        project_id: int,
        user_id: int,
        include_unpublished: bool = False,
    ) -> TrainingOverviewResponse:
        courses = await TrainingService.list_courses(
            db,
            project_id=project_id,
            include_unpublished=include_unpublished,
        )
        chapters = await TrainingService.list_chapters(
            db,
            project_id=project_id,
            include_unpublished=include_unpublished,
        )
        all_chapters = chapters
        if not include_unpublished:
            all_chapters = await TrainingService.list_chapters(
                db,
                project_id=project_id,
                include_unpublished=True,
            )

        query = select(TrainingContent).where(
            _project_filter(TrainingContent.project_id, project_id)
        )
        if not include_unpublished:
            query = query.where(TrainingContent.published.is_(True))
        content_rows = await db.execute(
            query.order_by(
                TrainingContent.sort_order.asc(),
                TrainingContent.id.asc(),
            )
        )
        all_contents = list(content_rows.scalars().all())

        record_rows = await db.execute(
            select(TrainingRecord)
            .join(TrainingContent, TrainingContent.id == TrainingRecord.content_id)
            .where(
                TrainingRecord.user_id == user_id,
                _project_filter(TrainingContent.project_id, project_id),
            )
        )
        record_by_content_id = {
            record.content_id: record for record in record_rows.scalars().all()
        }

        chapter_ids = {chapter.id for chapter in chapters}
        all_chapter_ids = {chapter.id for chapter in all_chapters}
        contents_by_chapter: dict[int, list[TrainingContentProgressResponse]] = {}
        standalone_contents: list[TrainingContentProgressResponse] = []

        for content in all_contents:
            payload = _content_to_progress(content, record_by_content_id)
            if content.chapter_id is not None:
                if content.chapter_id in chapter_ids:
                    contents_by_chapter.setdefault(content.chapter_id, []).append(payload)
                elif content.chapter_id not in all_chapter_ids:
                    standalone_contents.append(payload)
                continue
            standalone_contents.append(payload)

        chapters_by_course: dict[int, list[TrainingChapterDetailResponse]] = {}
        for chapter in chapters:
            materials = contents_by_chapter.get(chapter.id, [])
            completed = sum(1 for item in materials if item.learned)
            total = len(materials)
            chapters_by_course.setdefault(chapter.course_id, []).append(
                TrainingChapterDetailResponse(
                    **TrainingChapterDetailResponse.model_validate(chapter).model_dump(),
                    materials=materials,
                    total_materials=total,
                    completed_materials=completed,
                    progress_percent=_progress_percent(completed, total),
                )
            )

        course_payloads: list[TrainingCourseDetailResponse] = []
        for course in courses:
            chapter_payloads = chapters_by_course.get(course.id, [])
            total = sum(item.total_materials for item in chapter_payloads)
            completed = sum(item.completed_materials for item in chapter_payloads)
            course_payloads.append(
                TrainingCourseDetailResponse(
                    **TrainingCourseDetailResponse.model_validate(course).model_dump(),
                    chapters=chapter_payloads,
                    total_materials=total,
                    completed_materials=completed,
                    progress_percent=_progress_percent(completed, total),
                )
            )

        standalone_completed = sum(1 for item in standalone_contents if item.learned)
        standalone_total = len(standalone_contents)
        total_materials = (
            sum(item.total_materials for item in course_payloads) + standalone_total
        )
        completed_materials = (
            sum(item.completed_materials for item in course_payloads)
            + standalone_completed
        )

        return TrainingOverviewResponse(
            courses=course_payloads,
            standalone_contents=standalone_contents,
            total_materials=total_materials,
            completed_materials=completed_materials,
            progress_percent=_progress_percent(completed_materials, total_materials),
        )

    @staticmethod
    async def list_contents(
        db: AsyncSession,
        project_id: int,
        include_unpublished: bool = False,
    ) -> List[TrainingContent]:
        query = select(TrainingContent).where(
            _project_filter(TrainingContent.project_id, project_id)
        )
        if not include_unpublished:
            query = query.where(TrainingContent.published.is_(True))
        result = await db.execute(
            query.order_by(
                TrainingContent.sort_order.asc(),
                TrainingContent.updated_at.desc(),
                TrainingContent.id.desc(),
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_content(
        db: AsyncSession,
        content_id: int,
        project_id: int,
    ) -> Optional[TrainingContent]:
        result = await db.execute(
            select(TrainingContent).where(
                TrainingContent.id == content_id,
                _project_filter(TrainingContent.project_id, project_id),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_content(
        db: AsyncSession,
        data: TrainingContentCreate,
        project_id: int,
    ) -> TrainingContent:
        if data.chapter_id is not None:
            chapter = await TrainingService.get_chapter(db, data.chapter_id, project_id)
            if not chapter:
                raise ValueError("Chapter not found in current project")

        content = TrainingContent(
            title=data.title,
            description=data.description,
            file_url=data.file_url,
            category_id=data.category_id,
            chapter_id=data.chapter_id,
            project_id=project_id,
            content_type=data.content_type,
            sort_order=data.sort_order,
            estimated_minutes=data.estimated_minutes,
            published=data.published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(content)
        await db.commit()
        await db.refresh(content)
        return content

    @staticmethod
    async def update_content(
        db: AsyncSession,
        content_id: int,
        data: TrainingContentUpdate,
        project_id: int,
    ) -> Optional[TrainingContent]:
        content = await TrainingService.get_content(db, content_id, project_id)
        if not content:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "chapter_id" in update_data and update_data["chapter_id"] is not None:
            chapter = await TrainingService.get_chapter(
                db, update_data["chapter_id"], project_id
            )
            if not chapter:
                raise ValueError("Chapter not found in current project")

        for field, value in update_data.items():
            setattr(content, field, value)
        content.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(content)
        return content

    @staticmethod
    async def delete_content(db: AsyncSession, content_id: int, project_id: int) -> bool:
        content = await TrainingService.get_content(db, content_id, project_id)
        if not content:
            return False
        await db.delete(content)
        await db.commit()
        return True

    @staticmethod
    async def mark_record(
        db: AsyncSession,
        user_id: int,
        data: TrainingRecordCreate,
        project_id: int,
    ) -> TrainingRecord:
        content_result = await db.execute(
            select(TrainingContent).where(
                TrainingContent.id == data.content_id,
                _project_filter(TrainingContent.project_id, project_id),
            )
        )
        content = content_result.scalar_one_or_none()
        if not content:
            raise ValueError("Content not found in current project")

        result = await db.execute(
            select(TrainingRecord).where(
                TrainingRecord.user_id == user_id,
                TrainingRecord.content_id == data.content_id,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.completed_at = data.completed_at or datetime.utcnow()
            await db.commit()
            await db.refresh(record)
            return record

        record = TrainingRecord(
            user_id=user_id,
            content_id=data.content_id,
            completed_at=data.completed_at or datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_records(
        db: AsyncSession,
        project_id: int,
        user_id: Optional[int] = None,
    ) -> List[TrainingRecord]:
        query = (
            select(TrainingRecord)
            .join(TrainingContent, TrainingContent.id == TrainingRecord.content_id)
            .where(_project_filter(TrainingContent.project_id, project_id))
        )
        if user_id is not None:
            query = query.where(TrainingRecord.user_id == user_id)
        result = await db.execute(query.order_by(TrainingRecord.completed_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def list_questions(db: AsyncSession, project_id: int) -> List[ExamQuestion]:
        result = await db.execute(
            select(ExamQuestion).where(_project_filter(ExamQuestion.project_id, project_id))
        )
        return result.scalars().all()

    @staticmethod
    async def create_question(
        db: AsyncSession, data: ExamQuestionCreate, project_id: int
    ) -> ExamQuestion:
        question = ExamQuestion(
            category_id=data.category_id,
            project_id=project_id,
            question=data.question,
            options=json.dumps(data.options or []),
            answer=json.dumps(data.answer),
            score=data.score,
            type=data.type,
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        return question

    @staticmethod
    async def update_question(
        db: AsyncSession,
        question_id: int,
        data: ExamQuestionUpdate,
        project_id: int,
    ) -> Optional[ExamQuestion]:
        result = await db.execute(
            select(ExamQuestion).where(
                ExamQuestion.id == question_id,
                _project_filter(ExamQuestion.project_id, project_id),
            )
        )
        question = result.scalar_one_or_none()
        if not question:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if "options" in update_data:
            update_data["options"] = json.dumps(update_data["options"] or [])
        if "answer" in update_data:
            update_data["answer"] = json.dumps(update_data["answer"])
        for field, value in update_data.items():
            setattr(question, field, value)
        await db.commit()
        await db.refresh(question)
        return question

    @staticmethod
    async def delete_question(db: AsyncSession, question_id: int, project_id: int) -> bool:
        result = await db.execute(
            select(ExamQuestion).where(
                ExamQuestion.id == question_id,
                _project_filter(ExamQuestion.project_id, project_id),
            )
        )
        question = result.scalar_one_or_none()
        if not question:
            return False
        await db.delete(question)
        await db.commit()
        return True

    @staticmethod
    async def list_rules(db: AsyncSession, project_id: int) -> List[ExamRule]:
        result = await db.execute(
            select(ExamRule).where(_project_filter(ExamRule.project_id, project_id))
        )
        return result.scalars().all()

    @staticmethod
    async def create_rule(
        db: AsyncSession, data: ExamRuleCreate, project_id: int
    ) -> ExamRule:
        rule = ExamRule(
            project_id=project_id,
            pass_score=data.pass_score,
            question_count=data.question_count,
            duration_minutes=data.duration_minutes,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def update_rule(
        db: AsyncSession,
        rule_id: int,
        data: ExamRuleUpdate,
        project_id: int,
    ) -> Optional[ExamRule]:
        result = await db.execute(
            select(ExamRule).where(
                ExamRule.id == rule_id,
                _project_filter(ExamRule.project_id, project_id),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, rule_id: int, project_id: int) -> bool:
        result = await db.execute(
            select(ExamRule).where(
                ExamRule.id == rule_id,
                _project_filter(ExamRule.project_id, project_id),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        await db.delete(rule)
        await db.commit()
        return True

    @staticmethod
    async def get_active_rule(db: AsyncSession, project_id: int) -> ExamRule:
        result = await db.execute(
            select(ExamRule)
            .where(_project_filter(ExamRule.project_id, project_id))
            .order_by(ExamRule.id.desc())
        )
        rule = result.scalars().first()
        if rule:
            return rule
        return ExamRule(
            pass_score=settings.EXAM_DEFAULT_PASS_SCORE,
            question_count=settings.EXAM_DEFAULT_QUESTION_COUNT,
            duration_minutes=settings.EXAM_DEFAULT_DURATION_MINUTES,
        )

    @staticmethod
    async def start_exam(
        db: AsyncSession,
        user_id: int,
        project_id: int,
    ) -> tuple[ExamAttempt, list[ExamQuestion], ExamRule]:
        rule = await TrainingService.get_active_rule(db, project_id)

        active_result = await db.execute(
            select(ExamAttempt)
            .where(
                ExamAttempt.user_id == user_id,
                _project_filter(ExamAttempt.project_id, project_id),
                ExamAttempt.completed_at.is_(None),
            )
            .order_by(ExamAttempt.started_at.desc())
            .limit(1)
        )
        active_attempt = active_result.scalar_one_or_none()
        if active_attempt and active_attempt.started_at:
            expire_at = active_attempt.started_at + timedelta(
                minutes=rule.duration_minutes
            )
            if datetime.utcnow() <= expire_at:
                question_ids = []
                if active_attempt.question_ids:
                    try:
                        question_ids = json.loads(active_attempt.question_ids)
                    except json.JSONDecodeError:
                        question_ids = []
                if question_ids:
                    q_result = await db.execute(
                        select(ExamQuestion).where(
                            ExamQuestion.id.in_(question_ids),
                            _project_filter(ExamQuestion.project_id, project_id),
                        )
                    )
                    question_map = {q.id: q for q in q_result.scalars().all()}
                    questions = [
                        question_map[qid] for qid in question_ids if qid in question_map
                    ]
                    return active_attempt, questions, rule
            else:
                active_attempt.completed_at = datetime.utcnow()
                active_attempt.score = 0
                active_attempt.passed = False
                await db.commit()

        count = rule.question_count
        result = await db.execute(
            select(ExamQuestion)
            .where(_project_filter(ExamQuestion.project_id, project_id))
            .order_by(func.rand())
            .limit(count)
        )
        questions = result.scalars().all()
        if not questions:
            raise ValueError("No exam questions configured")
        attempt = ExamAttempt(
            user_id=user_id,
            project_id=project_id,
            started_at=datetime.utcnow(),
            question_ids=json.dumps([q.id for q in questions]),
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt, questions, rule

    @staticmethod
    async def submit_exam(
        db: AsyncSession,
        attempt: ExamAttempt,
        answers: dict,
    ) -> ExamAttempt:
        if attempt.project_id is None:
            raise ValueError("Exam attempt is not bound to a project")
        if attempt.completed_at:
            return attempt

        rule = await TrainingService.get_active_rule(db, int(attempt.project_id))
        if attempt.started_at and datetime.utcnow() > attempt.started_at + timedelta(
            minutes=rule.duration_minutes
        ):
            attempt.score = 0
            attempt.passed = False
            attempt.completed_at = datetime.utcnow()
            attempt.answers = json.dumps(answers)
            await db.commit()
            await db.refresh(attempt)
            return attempt

        question_ids = []
        if attempt.question_ids:
            try:
                question_ids = json.loads(attempt.question_ids)
            except json.JSONDecodeError:
                question_ids = []
        if not question_ids:
            raise ValueError("Exam attempt has no questions")
        result = await db.execute(
            select(ExamQuestion).where(ExamQuestion.id.in_(question_ids))
        )
        questions = result.scalars().all()

        score = 0
        for q in questions:
            try:
                correct = json.loads(q.answer)
            except json.JSONDecodeError:
                correct = q.answer
            user_answer = answers.get(str(q.id)) if isinstance(answers, dict) else None
            if user_answer is None:
                user_answer = answers.get(q.id) if isinstance(answers, dict) else None

            if q.type == "multi":
                correct_values = correct if isinstance(correct, list) else [correct]
                user_values = user_answer if isinstance(user_answer, list) else [user_answer]
                if sorted([str(v) for v in user_values if v is not None]) == sorted(
                    [str(v) for v in correct_values if v is not None]
                ):
                    score += q.score
            elif q.type == "truefalse":
                if bool(user_answer) == bool(correct):
                    score += q.score
            else:
                if user_answer == correct:
                    score += q.score

        passed = score >= rule.pass_score
        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = datetime.utcnow()
        attempt.answers = json.dumps(answers)
        await db.commit()
        await db.refresh(attempt)
        return attempt
