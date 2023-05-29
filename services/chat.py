from services.openai import get_chat_completion, get_completion
import json


def generate_chat_response(context: str, question: str, model: str) -> str:
    messages = [
        {
            "role": "system",
            "content": f"""
            You are a very enthusiastic Supabase representative who loves to help people! 
            Given the following context sections , answer the question using only that information, outputted in markdown format. 
            If you are unsure and the answer is not explicitly written in the context sections, say "Sorry, I don't know how to help with that."

            context sections:
            {context}
            Question:
            {question}
            """,
        },
    ]

    if model == "gpt-3.5-turbo":
        completion = get_chat_completion(messages, model)
    else:
        completion = get_completion(messages[0]["content"], model)

    return completion