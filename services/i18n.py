import json
from models.i18n import i18n, LanguageMessage

class i18nAdapter():
    def __init__(self, local_json_file):
        with open(local_json_file) as f:
            self.json = json.load(f)
    
    def get_message(self, language: i18n, message: LanguageMessage):
        return self.json[language][message]