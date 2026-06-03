"""
Exam / Paper / Grading models.

Introduces the richer exam workflow on top of the existing flat ExamQuestion
model defined in app.models.training:
    question_bank            题库（项目内分组）
    exam_paper               试卷主表
    exam_paper_question      手动组卷（明确指定题目及分值）
    exam_paper_rule          随机组卷规则（按题库/题型/难度/数量抽题）
    exam_answer_item         每题作答（自动分+人工分+阅卷人）

The legacy ExamQuestion / ExamAttempt tables live in app.models.training and
have been extended with extra columns (bank_id / difficulty / knowledge_point
/ analysis / paper_id / total_score / manual_graded) to plug into this flow.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_question_bank_project_name"),
    )

    questions = relationship(
        "ExamQuestion",
        primaryjoin="QuestionBank.id == foreign(ExamQuestion.bank_id)",
        viewonly=True,
    )


class ExamPaper(Base):
    __tablename__ = "exam_paper"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    # manual: 使用 exam_paper_question 明确指定每道题
    # random: 每次开考时按 exam_paper_rule 抽题快照
    compose_type = Column(String(20), default="manual", nullable=False)
    total_score = Column(Integer, default=0, nullable=False)
    pass_score = Column(Integer, default=60, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    # 是否允许学员提交后立刻看到对错/解析
    show_result_immediately = Column(Boolean, default=False, nullable=False)
    # 是否对学员可见（可发布/下架）
    published = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    questions = relationship(
        "ExamPaperQuestion",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ExamPaperQuestion.sort_order",
    )
    rules = relationship(
        "ExamPaperRule",
        back_populates="paper",
        cascade="all, delete-orphan",
    )


class ExamPaperQuestion(Base):
    """手动组卷：试卷 ↔ 题目 关联（支持覆盖单题分数）。"""

    __tablename__ = "exam_paper_question"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(
        Integer,
        ForeignKey("exam_paper.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("exam_question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, default=0, nullable=False)
    # 如果 None，使用 question.score
    score_override = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("paper_id", "question_id", name="uq_paper_question"),
    )

    paper = relationship("ExamPaper", back_populates="questions")
    question = relationship("ExamQuestion")


class ExamPaperRule(Base):
    """随机组卷规则：按 题库 × 题型 × 难度区间 抽 N 题，每题按 score_per_question 给分。"""

    __tablename__ = "exam_paper_rule"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(
        Integer,
        ForeignKey("exam_paper.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_id = Column(
        Integer,
        ForeignKey("question_bank.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # 题型限定；None 表示不限
    question_type = Column(String(20), nullable=True)
    # 难度闭区间；默认 1..5 全量
    difficulty_min = Column(Integer, default=1, nullable=False)
    difficulty_max = Column(Integer, default=5, nullable=False)
    count = Column(Integer, default=1, nullable=False)
    score_per_question = Column(Integer, default=1, nullable=False)
    # 可选：限定知识点，为空表示不限
    knowledge_point = Column(String(100), nullable=True)

    paper = relationship("ExamPaper", back_populates="rules")


class ExamAnswerItem(Base):
    """每道题的作答快照，支持主观题人工阅卷。"""

    __tablename__ = "exam_answer_item"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(
        Integer,
        ForeignKey("exam_attempt.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("exam_question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 卷面原题分值快照（防止题目修改影响历史成绩）
    full_score = Column(Integer, default=0, nullable=False)
    # 作答内容（JSON 文本；客观题是 option index 或 bool，主观题是字符串）
    answer = Column(Text, nullable=True)
    # 客观题自动判分；主观题为 None，由 grader 填 manual_score
    auto_score = Column(Integer, nullable=True)
    manual_score = Column(Integer, nullable=True)
    # 最终得分：客观题 = auto_score；主观题 = manual_score；未批改为 None
    final_score = Column(Integer, nullable=True)
    grader_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime, nullable=True)
    comment = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    attempt = relationship(
        "ExamAttempt",
        back_populates="answer_items",
        foreign_keys=[attempt_id],
    )
    question = relationship("ExamQuestion")
