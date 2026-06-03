"""
Tool category model
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ToolCategory(Base):
    __tablename__ = "tool_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    tools = relationship("Tool", back_populates="category")

    def __repr__(self):
        return f"<ToolCategory(id={self.id}, name='{self.name}')>"
