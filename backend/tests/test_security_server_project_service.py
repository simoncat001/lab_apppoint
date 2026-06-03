from sqlalchemy.exc import OperationalError

import pytest

from app.services.security_server_project_service import SecurityServerProjectService


class _PermissionDeniedDb:
    async def execute(self, *args, **kwargs):
        raise OperationalError(
            "SELECT ... FROM `security-server`.`user`",
            {},
            Exception("SELECT command denied to user"),
        )


@pytest.mark.asyncio
async def test_permission_snapshot_db_error_falls_back_to_non_admin():
    snapshot = await SecurityServerProjectService.get_permission_snapshot_for_username_from_db(
        _PermissionDeniedDb(),
        username="admin",
    )

    assert snapshot.is_super_admin is False
    assert snapshot.is_admin is False
