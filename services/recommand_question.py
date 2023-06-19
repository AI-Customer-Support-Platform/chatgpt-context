from datastore.providers import qdrant_datastore, redis_chat
from models.i18n import i18nAdapter
from services.chat import chat_response
from services.openai import get_chat_completion
from typing import List
from models.models import Query
import json
import asyncio

datastore = qdrant_datastore.QdrantDataStore()
cache = redis_chat.RedisChat()
i18n_adapter = i18nAdapter("languages/local.json")
sem = asyncio.Semaphore(2)

def generate_question(query_list: List[str], language: str) -> List[str]:
    query_content = ""

    for query in query_list:
        query_content += f"- {query}\n "
    
    messages = [
        {
            "role": "system",
            "content": f"Please convert the following keywords into questions. Output 5 {language} questions and their corresponding keyword in JSONL format. Only need JSONL return"
        },
        {
            "role": "user",
            "content": query_content
        }
    ]

    question_list = get_chat_completion(messages, temperature=0)
    
    print(generate_question)
    result_list = []

    for question_with_keywords in question_list.split("\n"):
        result_list.append(json.loads(question_with_keywords))

    return result_list


async def answer_question(lang: str, language: str, collection: str):
    query_list = cache.get_key_word(lang)
    question_list = generate_question(query_list, language)

    cache.redis.delete(f"{lang}DailyQuestion")

    for question in question_list:
        print(question)
        user_question = question["question"]


        query_results = await datastore.query(
            [Query(query=user_question, top_k=3)],
            collection
        )

        content = chat_response(
            context=query_results[0].results, 
            user_question=user_question,
            sorry=i18n_adapter.get_message(lang, message="sorry")
        )
        
        cache.add_faq(user_question, content, lang)
        print(f"{user_question} OK") 

async def generate_faq():
    async with sem:
        for lang in i18n_adapter.get_support_language():
            language = i18n_adapter.get_message(lang, "language")
            await answer_question(lang, language, "microsoft")  