import redis
import os

from models.chat import ChatHistory, QAHistory
from typing import List
from utils.common import singleton_with_lock

import codecs

REDIS_URL = os.environ.get("UPSTASH_REDIS_URL", "redis://localhost:6379")


@singleton_with_lock
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
        try:
            chat_history = self.redis.json().get(user_id, "$")[0]
        except TypeError:
            chat_history = []
            
        return chat_history

    def user_exists(self, user_id: bytes) -> bool:
        return self.redis.exists(user_id)
    
    def add_question_key_word(self, query: str, language: str):
        self.redis.zincrby(f"{language}QuestionKeyWord", 1, query)
    
    def get_key_word(self, collection: str) -> List[str]:
        result = self.redis.zrange(collection, 0, 4, desc=True)
        return list(map(codecs.decode, result))
    
    def add_not_answer_key_world(self, query: str, language: str):
        self.redis.zrem(f"{language}QuestionKeyWord", query)
        self.redis.zincrby("NotAnswerKeyWord", 1, query)
    
    def add_faq(self, question: str, answer: str, language: str):
        self.redis.hset(f"{language}DailyQuestion", question, answer)
    
    def get_faq_question(self, language: str) -> List[str]:
        question_list = self.redis.hkeys(f"{language}DailyQuestion")
        try:
            question_str_list = list(map(codecs.decode, question_list))
        except TypeError:
            question_str_list = []
        
        return question_str_list

    def get_faq_answer(self, question: str, language: str) -> str:
        try:
            answer = self.redis.hget(f"{language}DailyQuestion", question)
            answer_str = codecs.decode(answer)
        except TypeError:
            answer_str = ""
        return answer_str