from typing import Optional, List, Union
from enum import Enum
from models.i18n import i18n
from pydantic import BaseModel

class QAHistory(BaseModel):
    user_question: str
    answer: str


class ChatHistory(QAHistory):
    query: Optional[str] = None
    background: str
    
class ChatHistortList(BaseModel):
    chat_history: Optional[List[ChatHistory]]

class AuthMetadata(BaseModel):
    auth: str
    uid: str


class WebsocketFlag(str, Enum):
    chat_v3 = "chat_v3"
    chat_v2 = "chat_v2"
    switch_lang = "switch_lang"
    authorized = "authorized"
    questions = "questions"
    v2_req = "v2_req"
    answer_start = "answer::start"
    answer_body = "answer::body"
    answer_end = "answer::end"


class SwitchLanguage(BaseModel):
    language: i18n


class ChatV2Message(BaseModel):
    question: str
    v2_token: str
    cache: Optional[bool] = False


class ChatV3Message(BaseModel):
    question: str
    v3_token: str
    cache: Optional[bool] = False


class WebsocketMessage(BaseModel):
    type: WebsocketFlag
    content: Optional[Union[SwitchLanguage, ChatV2Message, ChatV3Message, List[str], str]] = ""

