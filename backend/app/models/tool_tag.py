"""
Tool tag model
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.tool_tag_link import tool_tag_link


class ToolTag(Base):
    __tablename__ = "tool_tag"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    tools = relationship(
        "Tool",
        secondary=tool_tag_link,
        back_populates="tags",
    )

    def __repr__(self):
        return f"<ToolTag(id={self.id}, name='{self.name}')>"
