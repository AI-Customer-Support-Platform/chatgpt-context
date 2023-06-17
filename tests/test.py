import json
import asyncio

import openai
from typing import List
from models.models import Query

from services.openai import get_chat_completion
from datastore.providers import qdrant_datastore, redis_chat
from models.openai_schemas import OpenAIChatResponse


datastore = qdrant_datastore.QdrantDataStore()

query_schema = [
    {
        "name": "query_background_knowledge",
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

async def generate_chat(user_question: str):
    messages = [
        { "role": "system", "content": "You are a helpful assistant. Check for background knowledge before answering user questions." },
        {
            "role": "user",
            "content": user_question
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=query_schema,

        # function_call={"name": "query_context"},  # auto is default, but we'll be explicit
    )

    response_message = response["choices"][0]["message"]

    if response_message.get("function_call"):
        function_name = response_message["function_call"]["name"]
        function_args = json.loads(response_message["function_call"]["arguments"])
        match function_name:
            case "query_background_knowledge":
                function_response = await query_background_knowledge(
                    query=function_args.get("key_word")
                )
            case "get_balance":
                function_response = "1000 USD"

        messages.append(response_message)
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )

        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )
        
        print("Function Result: ")
        print(second_response["choices"][0]["message"])

    else:
        print(response_message)

async def query_background_knowledge(query: str) -> str:
    query_results = await datastore.query(
        [Query(query=query, top_k=3)],
        "microsoft"
    )

    context_str = ""
    for doc in query_results[0].results:
        context_str += f"{doc.text}\n\"\"\"\n"

    return context_str
    
if __name__ == '__main__':
    asyncio.run(generate_chat("Check my balance"))
