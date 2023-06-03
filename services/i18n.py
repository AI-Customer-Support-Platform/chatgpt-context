import json
from models.i18n import i18n

class i18nAdapter():
    def __init__(self, local_json_file):
        with open(local_json_file) as f:
            self.json = json.load(f)
    
    def get_greetings(self, language: i18n):
        return self.json[language]["greetings"]