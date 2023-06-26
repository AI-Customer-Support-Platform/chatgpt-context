from datastore.providers import redis_chat, qdrant_datastore
from models.i18n import i18nAdapter
from services.chat import chat_response
from services.openai import get_chat_completion
from server.db.database import SessionLocal
from server.db import crud

from typing import List
from models.models import Query
import json
import asyncio
import datetime

from utils.schedulers import AsyncIOSchedulerWrapper

datastore = qdrant_datastore.QdrantDataStore()
cache = redis_chat.RedisChat()
i18n_adapter = i18nAdapter("languages/local.json")
sem = asyncio.Semaphore(2)
db = SessionLocal()
scheduler = AsyncIOSchedulerWrapper()

def generate_question(query: str, language: str) -> str:
    query_content = ""
    
    messages = [
        {
            "role": "system",
            "content": f"Please convert the following keywords into {language} questions. Return only one question"
        },
        {
            "role": "user",
            "content": query
        }
    ]

    question = get_chat_completion(messages, temperature=0)
    
    return question


async def answer_question(lang: str, query: str, question: str, collection: str):

    query_results = await datastore.query(
        [Query(query=query, top_k=3)],
        collection
    )

    content = chat_response(
        context=query_results[0].results, 
        user_question=question,
        sorry=i18n_adapter.get_message(lang, message="sorry")
    )
    
    print(f"{question} OK") 

    return content

async def collection_question_recommand(collecion_id: str):
    for lang in i18n_adapter.get_support_language():
        language = i18n_adapter.get_message(lang, "language")
        query_set = cache.get_key_word(lang, collecion_id)
        if not query_set:
            continue

        cache_set = cache.get_keyword_cache(lang, collecion_id)

        print(f"Cache set: {cache_set}")

        add_key_word = query_set - cache_set
        delete_key_word = cache_set - query_set

        print(f"Add Key Word: {add_key_word}")
        print(f"Delete Key Word: {delete_key_word}")

        if add_key_word:
            print("Add Key Word")
            for key_word in add_key_word:
                question = generate_question(key_word, language)
                answer = await answer_question(lang, key_word, question, collecion_id)

                cache.add_faq(key_word, question, answer, lang, collecion_id)

        if delete_key_word:
            print("Delete Key Word")
            for key_word in delete_key_word:
                cache.delete_faq(key_word, lang, collecion_id)

        cache.set_keyword_cache(query_set, lang, collecion_id)

async def generate_faq():
    collection_ids = crud.get_collection_list(db)
    start_date = datetime.datetime.now()
    async with sem:
        for collecion_id in collection_ids:
            run_date = datetime.datetime.now() + datetime.timedelta(minutes=5)
            scheduler.add_job(
                func=collection_question_recommand,
                args=(collecion_id,),
                trigger="date",
                run_date=run_date,
            )