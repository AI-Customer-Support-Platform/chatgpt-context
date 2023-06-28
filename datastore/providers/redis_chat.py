import redis
import os

from models.chat import ChatHistory, QAHistory
from typing import List, Set
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
    
    def add_question_key_word(self, query: str, language: str, collection: str):
        # self.redis.zincrby(f"{language}QuestionKeyWord", 1, query)
        self.redis.zincrby(f"{collection}::{language}::QuestionKeyWord", 1, query)
    
    def get_key_word(self, language: str, collection: str) -> Set[str]:
        result = self.redis.zrange(f"{collection}::{language}::QuestionKeyWord", 0, 4, desc=True)
        return set(map(codecs.decode, result))
    
    def add_not_answer_key_world(self, query: str, language: str, collection: str):
        self.redis.zrem(f"{collection}::{language}::QuestionKeyWord", query)
        self.redis.zincrby(f"{collection}::{language}::NotAnswerKeyWord", 1, query)
    
    def set_keyword_cache(self, query_list: Set[str], language: str, collection: str):
        self.redis.delete(f"{collection}::{language}::CacheKeyWord")
        self.redis.sadd(f"{collection}::{language}::CacheKeyWord", *query_list)
    
    def get_keyword_cache(self, language: str, collection: str) -> Set[str]:
        result = self.redis.smembers(f"{collection}::{language}::CacheKeyWord")
        return set(map(codecs.decode, result))

    def add_faq(self, keyword:str, question: str, answer: str, language: str, collection: str):
        self.redis.hset(f"{collection}::{language}::KeywordToQuestion", keyword, question)
        self.redis.hset(f"{collection}::{language}::QuestionToAnswer", question, answer)
    
    def delete_faq(self, keyword: str, language: str, collection: str):
        question = self.redis.hget(f"{collection}::{language}::KeywordToQuestion", keyword)

        self.redis.hdel(f"{collection}::{language}::KeywordToQuestion", keyword)
        self.redis.hdel(f"{collection}::{language}::QuestionToAnswer", question)

    def get_faq_question(self, language: str, collection: str) -> List[str]:
        question_list = self.redis.hkeys(f"{collection}::{language}::QuestionToAnswer")
        try:
            question_str_list = list(map(codecs.decode, question_list))
        except TypeError:
            question_str_list = []
        
        return question_str_list

    def get_faq_answer(self, question: str, language: str, collection: str) -> str:
        try:
            answer = self.redis.hget(f"{collection}::{language}::QuestionToAnswer", question)
            answer_str = codecs.decode(answer)
        except TypeError:
            answer_str = ""
        return answer_str
    
