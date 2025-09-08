from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del usuario")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    top_p: Optional[float] = Field(None, ge=0, le=1)


class ChatResponse(BaseModel):
    reply: str
    meta: Dict[str, Any] = Field(default_factory=dict)
