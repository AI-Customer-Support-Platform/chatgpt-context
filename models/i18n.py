import json
from enum import Enum
from utils.common import singleton_with_lock
class i18n(str, Enum):
    en = "en"
    ja = "ja"

class LanguageMessage(str, Enum):
    greetings = "greetings"

@singleton_with_lock
class i18nAdapter():
    def __init__(self, local_json_file):
        with open(local_json_file) as f:
            self.json = json.load(f)
    
    def get_message(self, language: i18n, message: LanguageMessage):
        return self.json[language][message]