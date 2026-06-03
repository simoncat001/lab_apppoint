from app.api.api import api_router


def _paths_for(method: str) -> list[str]:
    return [
        route.path
        for route in api_router.routes
        if method in getattr(route, "methods", set())
    ]


def test_task_action_routes_match_api_prefix_contract():
    assert "/tasks/{task_id}" in _paths_for("PUT")
    assert "/tasks/{task_id}/resolve" in _paths_for("POST")
    assert "/tasks/{task_id}/cancel" in _paths_for("POST")
    assert "/tasks/{task_id}" in _paths_for("DELETE")
    assert "/tasks/{task_id}/history" in _paths_for("GET")
    assert "/tasks/urgent" in _paths_for("GET")


def test_task_urgent_route_is_registered_before_task_detail_route():
    get_paths = _paths_for("GET")
    assert get_paths.index("/tasks/urgent") < get_paths.index("/tasks/{task_id}")
