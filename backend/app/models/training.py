"""Training and exam models."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class TrainingCategory(Base):
    __tablename__ = "training_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    courses = relationship("TrainingCourse", back_populates="category")
    contents = relationship("TrainingContent", back_populates="category")


class TrainingCourse(Base):
    __tablename__ = "training_course"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    cover_url = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey("training_category.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    sort_order = Column(Integer, default=0, nullable=False)
    published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    category = relationship("TrainingCategory", back_populates="courses")
    chapters = relationship(
        "TrainingChapter",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="TrainingChapter.sort_order, TrainingChapter.id",
    )


class TrainingChapter(Base):
    __tablename__ = "training_chapter"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(
        Integer,
        ForeignKey("training_course.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    course = relationship("TrainingCourse", back_populates="chapters")
    contents = relationship(
        "TrainingContent",
        back_populates="chapter",
        order_by="TrainingContent.sort_order, TrainingContent.id",
    )


class TrainingContent(Base):
    __tablename__ = "training_content"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey("training_category.id"), nullable=True)
    chapter_id = Column(
        Integer,
        ForeignKey("training_chapter.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    content_type = Column(String(20), default="link", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    estimated_minutes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    published = Column(Boolean, default=True, nullable=False)

    category = relationship("TrainingCategory", back_populates="contents")
    chapter = relationship("TrainingChapter", back_populates="contents")
    records = relationship("TrainingRecord", back_populates="content")


class TrainingRecord(Base):
    __tablename__ = "training_record"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    content_id = Column(
        Integer,
        ForeignKey("training_content.id", ondelete="CASCADE"),
        nullable=False,
    )
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    content = relationship("TrainingContent", back_populates="records")


class ExamQuestion(Base):
    __tablename__ = "exam_question"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("training_category.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    bank_id = Column(
        Integer,
        ForeignKey("question_bank.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=True)
    answer = Column(Text, nullable=False)
    score = Column(Integer, default=1, nullable=False)
    type = Column(String(20), default="single", nullable=False)
    difficulty = Column(Integer, default=3, nullable=False)
    knowledge_point = Column(String(100), nullable=True, index=True)
    analysis = Column(Text, nullable=True)

    category = relationship("TrainingCategory")


class ExamRule(Base):
    __tablename__ = "exam_rule"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    pass_score = Column(Integer, default=60, nullable=False)
    question_count = Column(Integer, default=10, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)


class ExamAttempt(Base):
    __tablename__ = "exam_attempt"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    paper_id = Column(
        Integer,
        ForeignKey("exam_paper.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Integer, default=0, nullable=False)
    total_score = Column(Integer, default=0, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    manual_graded = Column(Boolean, default=True, nullable=False)
    answers = Column(Text, nullable=True)
    question_ids = Column(Text, nullable=True)

    user = relationship("User")
    answer_items = relationship(
        "ExamAnswerItem",
        back_populates="attempt",
        cascade="all, delete-orphan",
        foreign_keys="ExamAnswerItem.attempt_id",
    )
