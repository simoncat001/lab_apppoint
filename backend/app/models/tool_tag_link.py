"""
Tool tag association table
"""
from sqlalchemy import Column, Integer, ForeignKey, Table

from app.db.session import Base

tool_tag_link = Table(
    "tool_tag_link",
    Base.metadata,
    Column("tool_id", Integer, ForeignKey("tool.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tool_tag.id", ondelete="CASCADE"), primary_key=True),
)
