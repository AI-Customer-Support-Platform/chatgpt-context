from pydantic import BaseModel
from typing import Optional
from enum import Enum

class i18n(str, Enum):
    en = "en"
    ja = "ja"

class LanguageMessage(BaseModel):
    greetings: str
    