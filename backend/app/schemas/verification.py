from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class VerificationCodeRequest(BaseModel):
    target: str = Field(..., min_length=3, max_length=200)
    type: Literal["email", "phone"]
    purpose: Literal["register", "login"]


class VerificationCodeResponse(BaseModel):
    target: str
    type: str
    purpose: str
    code: Optional[str] = None
    expires_at: datetime
