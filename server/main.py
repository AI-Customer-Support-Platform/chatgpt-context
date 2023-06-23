import os
import json
import uuid
import logging
import uvicorn
from fastapi import (
    FastAPI, 
    WebSocket, 
    WebSocketDisconnect, 
    HTTPException, 
    Depends, 
    Body,
    Cookie,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.api import knowledge_base

from models.api import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
)
from datastore.factory import get_datastore, get_redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.recommand_question import generate_faq
from services.chat import chat_switch

from models.models import Query
from models.i18n import i18n, i18nAdapter
from models.chat import AuthMetadata, WebsocketMessage, WebsocketFlag
from services.recaptcha import v2_captcha_verify, v3_captcha_verify


BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None

app = FastAPI()
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_base.router)

@app.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def chat_history(response: Response, user_id: str):
    try:
        user_bytes = uuid.UUID(user_id).bytes
    except ValueError:
        raise HTTPException(status_code=500, detail="badly formed hexadecimal UUID string")

    if cache.user_exists(user_bytes):
        history = cache.get_qa_history(user_bytes)
        exist_flag = True

    else:
        history = []
        exist_flag = False

    return ChatHistoryResponse(
        user_id=user_id, 
        history=history, 
        exist=exist_flag
    )

@app.post("/chat/{collection}", response_model=ChatResponse)
async def chat(
    collection: str,
    request: ChatRequest = Body(...),
):
    try:
        query_results = await datastore.query(
            [Query(query=request.question, topK=5)],
            collection
        )
        
        chat_response = await chat_switch(
            context=query_results[0].results,
            question=request.question,
            model=request.model,
        )

        return ChatResponse(response=chat_response, model=request.model)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error") 


@app.websocket("/ws/{collection}")
async def websocket_endpoint(collection: str, websocket: WebSocket):
    await websocket.accept()
    
    try:
        metadata_json = await websocket.receive_json()
        auth_metadata = AuthMetadata(**metadata_json)
    except:
        await websocket.close(1001, "authMetadata.decodeError")
        return
        
    if auth_metadata.auth != f"Bearer {BEARER_TOKEN}":
        await websocket.close(1002, "errors.unauthorized")
        return

    user_id = auth_metadata.uid
    user_uuid = uuid.UUID(user_id).bytes
    await websocket.send_json(WebsocketMessage(type="authorized").dict())

    language = i18n("en")

    while True:
        try:
            params = await websocket.receive_json()
            message = WebsocketMessage(**params)
        except WebSocketDisconnect:
            return
        except json.decoder.JSONDecodeError:
            await websocket.close(1003, "error.JSONDecode")
            return

        match message.type:
            case "switch_lang":
                language = i18n(message.content.language)
                sorry = i18n_adapter.get_message(language, message="sorry")

                await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_start).dict())

                await websocket.send_json(WebsocketMessage(
                    type=WebsocketFlag.answer_body, 
                    content=i18n_adapter.get_message(language, message="greetings")
                ).dict())

                await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_end).dict())

                await websocket.send_json(WebsocketMessage(
                    type=WebsocketFlag.questions, 
                    content=cache.get_faq_question(language)
                ).dict())

                continue

            case "chat_v2":
                recaptcha = v2_captcha_verify(user_uuid, message.content.v2_token)
            
            case "chat_v3":
                recaptcha = v3_captcha_verify(user_uuid, message.content.v3_token)


        if recaptcha:
            user_question = message.content.question
            cache_flag = message.content.cache
            print(f"{user_id} asked: {user_question}")

            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_start).dict())

            if cache_flag:
                cache_answer = cache.get_faq_answer(user_question, language)
                if cache_answer:
                    await websocket.send_json(WebsocketMessage(
                        type=WebsocketFlag.answer_body, 
                        content=cache_answer
                    ).dict())

                    cache.set_chat_history(user_uuid, {
                        "user_question": user_question,
                        "answer": cache_answer
                    })

                    await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_end).dict())

                    continue
            
            chat_response = await chat_switch(
                question=user_question,  
                history=cache.get_chat_history(user_uuid), 
                collection=collection, 
                language=language,
                sorry=sorry
            )
            content = ""
            async for data in chat_response:
                content += data

                await websocket.send_json(WebsocketMessage(
                    type=WebsocketFlag.answer_body, 
                    content=data
                ).dict())
            
            cache.set_chat_history(user_uuid, {
                "user_question": user_question,
                "answer": content
            })

            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_end).dict())

        else:
            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.v2_req).dict())
            continue

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()

    global cache
    cache = await get_redis()

    global i18n_adapter
    i18n_adapter = i18nAdapter("languages/local.json")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        func=generate_faq,
        trigger="cron",
        hour=0,
        minute=0,
        timezone="UTC",
        id="generate_faq",
        name="generate_faq",
        replace_existing=True,
    )
    scheduler.start()

def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
