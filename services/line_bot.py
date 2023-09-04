import aiohttp

from typing import List
from services.chat import chat_line
from models.chat import ChatHistory
from datastore.providers.redis_chat import RedisChat
from loguru import logger

async def line_reply(
    reply_token: str, 
    question: str,
    history: List[ChatHistory], 
    user_id: str,
    collection: str, 
    language: str, 
    sorry: str,
    cache: RedisChat
) -> str:
    answer, token_usage = await chat_line(
        question=question,
        history=history,
        collection=collection,
        language=language,
        sorry=sorry
    )

    cache.set_chat_history( user_id, {
        "user_question": question,
        "answer": answer
    })

    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": answer
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.line.me/v2/bot/message/reply", json=data) as resp:
            resp = await resp.text()
            logger.debug(resp)
            
    return answer, token_usage