from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.collaboration_service import CollaborationPermissionError, CollaborationService


def _user(
    user_id: int,
    *,
    is_staff: bool = False,
    is_superuser: bool = False,
    managed_tool_ids: list[int] | None = None,
):
    return SimpleNamespace(
        id=user_id,
        is_staff=is_staff,
        is_superuser=is_superuser,
        managed_tool_ids_list=managed_tool_ids or [],
    )


def _record(
    *,
    author_id: int = 1,
    tool_id: int | None = None,
    record_type: str = "tool_note",
    status: str = "draft",
    visibility: str = "project",
    deleted_at=None,
):
    return SimpleNamespace(
        id=10,
        author_id=author_id,
        tool_id=tool_id,
        record_type=record_type,
        status=status,
        visibility=visibility,
        deleted_at=deleted_at,
    )


def test_author_can_publish_own_regular_record():
    record = _record(author_id=1, record_type="tool_note", status="draft")
    user = _user(1)

    CollaborationService.ensure_can_publish(user, record)


def test_author_can_publish_own_issue_record():
    record = _record(author_id=1, record_type="issue", status="draft")
    user = _user(1)

    CollaborationService.ensure_can_create(user, record)
    CollaborationService.ensure_can_publish(user, record)


def test_regular_author_cannot_publish_knowledge_record():
    record = _record(author_id=1, tool_id=3, record_type="sop", status="draft")
    user = _user(1)

    with pytest.raises(CollaborationPermissionError):
        CollaborationService.ensure_can_publish(user, record)


def test_tool_manager_can_publish_knowledge_record_for_managed_tool():
    record = _record(author_id=2, tool_id=3, record_type="sop", status="draft")
    user = _user(1, is_staff=True, managed_tool_ids=[3])

    CollaborationService.ensure_can_publish(user, record)


def test_author_cannot_edit_archived_record():
    record = _record(author_id=1, status="archived")
    user = _user(1)

    with pytest.raises(CollaborationPermissionError):
        CollaborationService.ensure_can_update(user, record)


def test_project_visible_record_can_be_read_by_project_user():
    record = _record(visibility="project")
    user = _user(2)

    CollaborationService.ensure_can_read(user, record)


def test_private_record_can_only_be_read_by_author_or_manager():
    record = _record(author_id=1, tool_id=3, visibility="author_private")
    user = _user(2)

    with pytest.raises(CollaborationPermissionError):
        CollaborationService.ensure_can_read(user, record)


def test_soft_deleted_record_is_not_readable():
    record = _record(deleted_at=datetime.utcnow())
    user = _user(1)

    with pytest.raises(CollaborationPermissionError):
        CollaborationService.ensure_can_read(user, record)
