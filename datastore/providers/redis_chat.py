import redis
import os

from models.chat_history import ChatHistory, QAHistory
from typing import List

REDIS_URL = os.environ.get("UPSTASH_REDIS_URL", "redis://localhost:6379")

class RedisChat():
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
    
    def set_chat_history(self, user_id: bytes, chat_history: ChatHistory):
        if not self.redis.exists(user_id):
            self.redis.json().set(user_id, "$", [])
            self.redis.expire(user_id, 1800)
            
        self.redis.json().arrappend(user_id, "$", chat_history)
    
    def get_qa_history(self, user_id: bytes) -> List[QAHistory]:
        chat_history = self.redis.json().get(user_id, "$")[0]
        qa_list = []
        for chat in chat_history:
            qa_list.append(QAHistory(**chat))

        return qa_list
    
    def get_chat_history(self, user_id: bytes) -> List[ChatHistory]:
        chat_history = self.redis.json().get(user_id, "$")[0]
        return chat_history

    def user_exists(self, user_id: bytes) -> bool:
        return self.redis.exists(user_id)
