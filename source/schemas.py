from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    """Represents a single message in the conversational history."""
    role: str
    content: str

class ChatRequest(BaseModel):
    """Payload structure for incoming chat inference requests."""
    messages: List[Message]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 1024

class ChatResponse(BaseModel):
    """Structure of the API response returned to the client."""
    reply: str
    retrieved_context: str
    processing_time: float