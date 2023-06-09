import json
import asyncio

from datastore.factory import get_datastore
from services.chat import generate_chat
from models.models import Query


def import_data(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    return data


async def transform_data(data):
    datastore = await get_datastore()
    
    query_list = []
    input_list = []

    for line in data:
        query_list.append(Query(query=line["question"]))
    
    query_result_list = await datastore.query(query_list, "microsoft")

    for query_result in query_result_list:
        input_list.append({
            "question": query_result.query,
            "input": generate_chat(
                query_result.results, 
                question=query_result.query, 
                sorry="申し訳ありませんが、この質問にどう答えてよいかわかりません"
            )
        })
    
    transform_list = [
        {"input": input_chat["input"], "ideal": faq["answer"]}
        for input_chat, faq in zip(input_list, data)
    ]
    
    

    return transform_list

async def main():
    data = import_data(r"eval/data/faq-ja.json")
    result = await transform_data(data)
    
    with open(r'eval/data/faq-ja.jsonl', 'w', encoding="utf-8") as f:
        for item in result:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    

if __name__ == "__main__":
    asyncio.run(main())