from services.openai import get_chat_completion, get_completion
from models.models import DocumentChunkWithScore
from models.openai_schemas import OpenAIChatResponse
from models.chat import ChatHistory
from models.nlp_schemas import Classify
from typing import List

import openai
import json
import re

SEARCH = re.compile(r"<search>(.*)<\/search>")

def classify_question(question: str) -> Classify:
    messgaes = [
        {
            "role": "system",
            "content": """
            You will be provided with customer service queries. 
            Classify each query into a category.
            Provide your output in json format with the keys.

            sentiment:
                - negative
                - neutral
                - positive
            """
        },
        {
            "role": "user",
            "content": "I am very worried about the data problem, can you help me?"
        },
        {
            "role": "assistant",
            "content": """{"sentiment": "negative"}"""
        },
        {
            "role": "user",
            "content": question
        }
    ]

    completion = get_chat_completion(messgaes, temperature=0)

    try:
        result = Classify(**json.loads(completion))
    except:
        result = Classify(sentiment="neutral")
    
    return result


def generate_chat(context: str, question: str, sorry: str) -> List[str]:
    # print(f"Context: {context}")
    messages = [
        {
            "role": "system",
            "content": f"""
            Use the provided articles delimited by triple quotes to answer "User_Question". If the answer cannot be found in the articles, write "{sorry}"
            Only return answer content.

            {context}\nUser_Question: {question}
            Answer:\n
            """
        }
    ]

    return messages


def negative_chat(context: str, user_question: str, sorry: str) -> List[str]:
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
            """
        }
    ]

    return messages

async def generate_chat_response_async(context: List[DocumentChunkWithScore], user_question: str, sorry: str) -> str:
    context_str = ""
    for doc in context:
        context_str += f"{doc.text}\n\"\"\"\n"
    # print(f"Sorry: {sorry}")
    sentiment = classify_question(user_question).sentiment

    if sentiment == "negative":
        messages = negative_chat(context_str, user_question, sorry)
    else:
        messages = generate_chat(context_str, user_question, sorry)

    stream_answer = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, stream=True, temperature=0
    )
    # print(messages)
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
    if len(history) == 0:
        practice_round = {
            "user_question": "Who are the founders of OpenAI?",
            "query": "<search>OpenAI founders</search>",
            "background": "<result>The organization was founded in San Francisco in 2015 by Sam Altman, Reid Hoffman, Jessica Livingston, Elon Musk, Ilya Sutskever, Peter Thiel and others, who collectively pledged US$ 1 billion. Musk resigned from the board in 2018 but remained a donor.</result>",
            "answer": "The founders of OpenAI are Sam Altman, Reid Hoffman, Jessica Livingston, Elon Musk, Ilya Sutskever, Peter Thiel and others."
        }
    elif len(history) == 1:
        practice_round = history[0]
    else:
        practice_round = history[-2]

    
    prompt.extend([
        {
            "role": "user",
            "content": """
            From now on, whenever your response depends on any factual information, please search the web by using the function <search>query</search> before responding. 
            You only need to return the content of the search, no question answering is required.
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

    if len(history) > 1:
        chat = history[-1]
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
    completion = get_chat_completion(prompt, temperature=0)

    search_query = re.match(SEARCH, completion).group(1)

    return search_query