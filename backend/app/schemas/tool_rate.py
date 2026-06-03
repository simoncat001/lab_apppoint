from datetime import time
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ToolRateBase(BaseModel):
    tool_id: int
    start_time: time
    end_time: time
    price: float = Field(..., gt=0)

class ToolRateCreate(ToolRateBase):
    pass

class ToolRateUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    price: Optional[float] = None

class ToolRateResponse(ToolRateBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
