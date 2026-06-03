from app.models.tool import Tool
from app.schemas.tool import Tool as ToolSchema


def test_tool_model_has_persistent_created_at_column():
    assert hasattr(Tool, "created_at")


def test_tool_response_schema_exposes_created_at():
    assert "created_at" in ToolSchema.model_fields
