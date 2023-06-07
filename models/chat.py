from typing import Optional, List, Union
from enum import Enum
from models.i18n import i18n
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


class AuthMetadata(BaseModel):
    auth: str
    uid: str


class WebsocketFlag(str, Enum):
    chat_v3 = "chat_v3"
    chat_v2 = "chat_v2"
    switch_lang = "switch_lang"


class SwitchLanguage(BaseModel):
    language: i18n


class ChatV2Message(BaseModel):
    question: str
    v2_token: str


class ChatV3Message(BaseModel):
    question: str
    v3_token: str


class WebsocketMessage(BaseModel):
    type: WebsocketFlag
    content: Union[SwitchLanguage, ChatV2Message, ChatV3Message]