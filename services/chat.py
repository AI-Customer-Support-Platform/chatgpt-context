from services.openai import get_chat_completion, get_completion
from models.models import DocumentChunkWithScore
from models.openai_schemas import OpenAIChatResponse
from models.chat_history import ChatHistory
from models.chat_history import ChatHistory
from typing import List

import openai
import json
import re

SEARCH = re.compile(r"<search>(.*)<\/search>")

def generate_chat_response(context: List[DocumentChunkWithScore], question: str, model: str) -> str:
    result = ""
    for doc in context:
        result += f"<Result>{doc.text}</Result>\n"

    messages = [
        {
            "role": "system",
            "content": f"""
            You are a very enthusiastic customer service who loves to help people! 
            Given the following context sections, answer the question using only that information, outputted in markdown format. Only return answer content. 
            If you are unsure and the answer is not explicitly written in the context sections, say "Sorry, I don't know how to help with that."

            context sections:
            {result}
            Question:
            {question}
            """,
        }
    ]

    if model == "gpt-3.5-turbo":
        completion = get_chat_completion(messages, model)
    else:
        completion = get_completion(messages[0]["content"], model)

    return completion

async def generate_chat_response_async(context: List[DocumentChunkWithScore], question: str) -> str:
    result = ""
    for doc in context:
        result += f"<Result>{doc.text}</Result>\n"

    messages = [
        {
            "role": "system",
            "content": f"""
            You are a very enthusiastic customer service who loves to help people! 
            Given the following context sections, answer the question using only that information, outputted in markdown format. Only return answer content. 
            If you are unsure and the answer is not explicitly written in the context sections, say "Sorry, I don't know how to help with that."

            context sections:
            {result}
            Question:
            {question}
            """,
        }
    ]

    stream_answer = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, stream=True
    )

    content = ""
    for chunk in stream_answer:
        resp = OpenAIChatResponse(**chunk)
        if resp.choices[0].delta is not None:
            content += resp.choices[0].delta.get("content", "")
        elif chunk.choices[0].finish_reason == "stop":
            continue

        yield content

def history_to_query(question: str, history: List[ChatHistory]) -> str:
    prompt = []
    practice_round = history[0]
    prompt.extend([
        {
            "role": "user",
            "content": """
            From now on, whenever your response depends on any factual information, please search the web by using the function <search>query</search> before responding. 
            You only need to return the content of the search, no question answering is required
            I will then paste web results in, and you can respond.
            """
        },
        {
            "role": "assistant",
            "content": "Ok, I will do that. Let's do a practice round"
        },
        {
            "role": "user",
            "content": practice_round["user_question"]
        },
        {
            "role": "assistant",
            "content": practice_round["query"]
        },
        {
            "role": "user",
            "content": practice_round["background"]
        },
        {
            "role": "assistant",
            "content": practice_round["answer"]
        },
        {
            "role": "assistant",
            "content": "Ok, I'm ready."
        }
    ])

    for chat in history[1:]:
        prompt.extend([
            {
                "role": "user",
                "content": chat["user_question"]
            },
            {
                "role": "assistant",
                "content": chat["query"]
            },
            {
                "role": "user",
                "content": chat["background"]
            },
            {
                "role": "assistant",
                "content": chat["answer"]
            }
        ])
    
    prompt.extend([
        {
            "role": "user",
            "content": question
        }
    ])

    # print(prompt)
    completion = get_chat_completion(prompt)

    search_query = re.match(SEARCH, completion).group(1)

    return search_query