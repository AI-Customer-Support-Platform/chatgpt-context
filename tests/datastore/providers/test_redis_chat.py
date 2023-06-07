from datastore.providers.redis_chat import RedisChat
from models.chat import ChatHistory
import pytest


@pytest.fixture
def redis_chat() -> RedisChat:
    redis_chat = RedisChat()
    if redis_chat.user_exists(b"user_id"):
        redis_chat.redis.delete(b"user_id")
    return redis_chat


def test_set_chat_history(redis_chat):
    write_chat_history =  ChatHistory(
        user_question="user_question", query="query", background="background", answer="answer"
    )

    redis_chat.set_chat_history(b"user_id", write_chat_history.dict())

    assert redis_chat.get_chat_history(b"user_id") == [write_chat_history]

    redis_chat.redis.delete(b"user_id")

def test_get_qa_history(redis_chat):
    write_qa_history =  ChatHistory(
        user_question="user_question", query="query", background="background", answer="answer"
    )

    redis_chat.set_chat_history(b"user_id", write_qa_history.dict())

    assert redis_chat.get_qa_history(b"user_id") == [{"user_question": "user_question", "answer": "answer"}]

    redis_chat.redis.delete(b"user_id")