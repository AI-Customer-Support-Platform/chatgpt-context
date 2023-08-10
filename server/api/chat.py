import os
import uuid
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
    HTTPException, 
    Depends, 
    Body,
    Response,
    APIRouter
)

from models.api import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
)

from loguru import logger
from services.chat import chat_switch

from models.models import Query
from models.i18n import i18n, i18nAdapter
from models.chat import AuthMetadata, WebsocketMessage, WebsocketFlag
from services.recaptcha import v2_captcha_verify, v3_captcha_verify
from services.chunks import token_count

from datastore.providers.redis_chat import RedisChat
from server.api.deps import get_db
from server.db import crud
from sqlalchemy.orm import Session

router = APIRouter()
cache = RedisChat()
i18n_adapter = i18nAdapter("languages/local.json")

BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None

@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
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

@router.post("/chat/{collection}", response_model=ChatResponse)
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
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error") 


@router.websocket("/ws/{collection}")
async def websocket_endpoint(collection: str, websocket: WebSocket, db: Session = Depends(get_db)):
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

    try:
        stripe_id = crud.get_collection_stripe_id(db, cache.redis, collection)
    except AttributeError:
        await websocket.close(1002, "errors.PlansOrCollectionNotExists")
        return

    logger.debug(f"stripe_id: {stripe_id}")

    while True:
        try:
            params = await websocket.receive_json()
            message = WebsocketMessage(**params)
        except WebSocketDisconnect:
            return
        except json.decoder.JSONDecodeError:
            await websocket.close(1003, "error.JSONDecode")
            return
        except:
            await websocket.close(1004, "errors.Data")
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
                    content=cache.get_faq_question(language, collection)
                ).dict())

                continue

            case "chat_v2":
                recaptcha = v2_captcha_verify(user_uuid, message.content.v2_token)
            
            case "chat_v3":
                recaptcha = v3_captcha_verify(user_uuid, message.content.v3_token)


        if recaptcha:
            user_question = message.content.question
            cache_flag = message.content.cache
            logger.info(f"{user_id} asked: {user_question}")

            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_start).dict())

            if cache_flag:
                cache_answer = cache.get_faq_answer(user_question, language, collection)
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
            
            if cache.redis.exists(f"{stripe_id}::reach_limit"):
                await websocket.send_json(WebsocketMessage(
                    type=WebsocketFlag.answer_body, 
                    content="limit reached"
                ).dict())

                await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_end).dict())

                continue

            chat_response, token_usage = await chat_switch(
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

            token_usage += token_count(content)
            logger.debug(f"token_usage: {token_usage}")
            crud.minus_token_remaining(db, cache.redis, stripe_id, token_usage)

            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.answer_end).dict())

        else:
            await websocket.send_json(WebsocketMessage(type=WebsocketFlag.v2_req).dict())
            continue