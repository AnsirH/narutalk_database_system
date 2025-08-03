from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatSessionBase(BaseModel):
    session_id: str
    employee_id: int
    session_title: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    is_archived: bool = False
    archived_at: Optional[datetime] = None

class ChatSessionCreate(BaseModel):
    session_id: str
    employee_id: int
    session_title: Optional[str] = None

class ChatSessionUpdate(BaseModel):
    session_title: Optional[str] = None

class ChatSessionResponse(ChatSessionBase):
    class Config:
        from_attributes = True 