from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str
    steps: Optional[List[dict]] = None # Allow steps in message for history if needed
    source: Optional[str] = None
    score: Optional[float] = None

class Step(BaseModel):
    name: str
    status: str
    timestamp: str
    error: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    target_language: str = "English"
    history: List[Message] = []
    stream: bool = False

class QueryResponse(BaseModel):
    response: str
    source: str = "Unknown"
    score: Optional[float] = None
    steps: List[Step] = []


