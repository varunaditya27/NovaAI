from pydantic import BaseModel
from typing import Optional, List

class Message(BaseModel):
    message_id: str
    session_id: str
    text: str
    quoted_reply_to: Optional[str] = None
    quoted_text: Optional[str] = None
    timestamp: str
    tags: Optional[List[str]] = []
    mood: Optional[str] = None

class MessageCreate(BaseModel):
    session_id: Optional[str] = None
    text: str
    quoted_reply_to: Optional[str] = None
    quoted_text: Optional[str] = None
    tags: Optional[List[str]] = []
    mood: Optional[str] = None

class Session(BaseModel):
    session_id: str
    created_at: str
    last_activity: str

class SessionSummary(BaseModel):
    summary: List[str]
    timestamp: str
    topics: List[str]
    session_id: str 