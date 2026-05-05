from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class ReviewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(Parent|Student|Tutor)$")
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1)


class ReviewResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    name: str
    role: Optional[str]
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime