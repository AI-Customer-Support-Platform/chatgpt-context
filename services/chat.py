from services.openai import get_chat_completion, get_completion
from models.models import DocumentChunkWithScore
from models.openai_schemas import OpenAIChatResponse
from models.chat import ChatHistory
from models.nlp_schemas import Classify
from models.models import Query
from typing import List

import openai
import json
import re
import random

from datastore.providers.qdrant_datastore import QdrantDataStore
from datastore.providers.azure_nlp import AzureClient
from datastore.providers.redis_chat import RedisChat
from models.i18n import i18nAdapter
from loguru import logger

datastore = QdrantDataStore()
nlp_client = AzureClient()
cache = RedisChat()
i18n_adapter = i18nAdapter("languages/local.json")

query_schema = [
    {
        "name": "ask_database",
        "description": "Get the background knowledge of the user's question",
        "parameters": {
            "type": "object",
            "properties": {
                "key_word": {
                    "type": "string",
                    "description": "Key words used for database retrieval" 
                }
            }
        }
    },
    {
        "name": "get_balance",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


async def chat_switch(question: str,  history: List[ChatHistory], collection: str, language: str,sorry: str):
    messages = [
        {
            "role": "system", 
            "content": "Before replying to user questions, please query the database." 
        }
    ]

    if len(history) > 0:
        messages.extend(
            [
                {
                    "role": "user",
                    "content": history[-1]["user_question"]
                },
                {
                    "role": "assistant",
                    "content": history[-1]["answer"]
                },
            ]
        )

    messages.append({
        "role": "user",
        "content": question
    })

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=query_schema,
        temperature=0
    )

    response_message = response["choices"][0]["message"]
    if response_message.get("function_call"):
        function_name = response_message["function_call"]["name"]
        function_args = json.loads(response_message["function_call"]["arguments"])
        logger.info(f"Function name: {function_name} Args: {function_args}")
        match function_name:
            case "ask_database":
                func = ask_database(
                    user_question=question,
                    query=function_args.get("key_word"),
                    collection=collection,
                    language=language,
                    sorry=sorry
                )

            case "get_balance":
                func = get_balance(
                    user_question=question
                )
    else:
        logger.warning(f"{question} Fallback")
        func = ask_database(
            user_question=question,
            query=question,
            collection=collection,
            language=language,
            sorry=sorry
        )
    
    return func


def normal_answer(context: str, question: str, sorry: str) -> List[str]:
    # print(f"Context: {context}")
    messages = [
        {
            "role": "system",
            "content": f"""
            Use the provided articles delimited by triple quotes to answer "User_Question". If the answer cannot be found in the articles, write "{sorry}"

            {context}\nUser_Question: {question}
            Answer (using markdown):\n
            """
        }
    ]

    return messages


def negative_answer(context: str, user_question: str, sorry: str) -> List[str]:
    # print(f"Context: {context}")
    messages = [
        {
            "role": "system",
            "content": f"""
            Please follow the steps below for question answering:

            Step 1: Please appease user_questions with negative emotions, the output is the first paragraph of the answer
            Step 2: Use the provided articles delimited by triple quotes to answer "user_question". If the answer cannot be found in the articles, write "{sorry}". the output is the second paragraph of the answer

            {context}

            user_question: {user_question}
            Answer (using markdown):\n
            """
        }
    ]

    return messages


async def ask_database(user_question: str, query: str, collection: str, language: str, sorry: str) -> str:
    query_results = await datastore.query(
        [Query(query=query, top_k=3)],
        collection
    )

    cache.add_question_key_word(query, language, collection)
    context_str = ""

    for doc in query_results[0].results:
        context_str += f"{doc.text}\n\"\"\"\n"
    
    sentiment = nlp_client.sentiment_analysis(user_question)
    logger.info(f"Quseion: {user_question} Sentiment: {sentiment}")
    # sentiment = classify_question(user_question).sentiment
    if sentiment == "negative":
        messages = negative_answer(context_str, user_question, sorry)
    else:
        messages = normal_answer(context_str, user_question, sorry)

    stream_answer = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, stream=True, temperature=0
    )
    # print(messages)
    final_result = ""
    for chunk in stream_answer:
        resp = OpenAIChatResponse(**chunk)
        if resp.choices[0].delta is not None:
            content = resp.choices[0].delta.get("content", "")
            final_result += content
            # Sorry 申
            if final_result.startswith(i18n_adapter.get_message(language, message="sorry")):
                print(f"{user_question} Can't Answer")
                cache.add_not_answer_key_world(query, language, collection)

        elif chunk.choices[0].finish_reason == "stop":
            continue

        yield content


def chat_response(context: List[DocumentChunkWithScore], user_question: str, sorry: str) -> str:
    context_str = ""
    for doc in context:
        context_str += f"{doc.text}\n\"\"\"\n"

    messages = normal_answer(context_str, user_question, sorry)

    answer = get_chat_completion(messages)

    return answer


async def get_balance(user_question: str):
    balance = random.randint(1000, 10000)
    messages = [
        {
            "role": "user",
            "content": user_question
        },
        {
            "role": "function",
            "name": "get_balance",
            "content": f"User balance is {balance} USD"
        }
    ]
    
    stream_answer = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        stream=True, 
        temperature=0
    )

    for chunk in stream_answer:
        resp = OpenAIChatResponse(**chunk)
        if resp.choices[0].delta is not None:
            content = resp.choices[0].delta.get("content", "")
        elif chunk.choices[0].finish_reason == "stop":
            continue

        yield content

async def fallback_func():
    for content in "Sorry, I don't know how to help with that":
        yield content