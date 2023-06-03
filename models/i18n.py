from enum import Enum

class i18n(str, Enum):
    en = "en"
    ja = "ja"

class LanguageMessage(str, Enum):
    greetings = "greetings"
    