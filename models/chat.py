from typing import Optional, List

from pydantic import BaseModel

class ChatHistory(BaseModel):
    user_question: str
    query: Optional[str] = None
    background: str
    answer: str
    
class ChatHistortList(BaseModel):
    chat_history: Optional[List[ChatHistory]]

class QAHistory(BaseModel):
    user_question: str
    answer: str