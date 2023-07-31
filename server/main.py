import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.api import knowledge_base, payment, chat
from models.i18n import i18nAdapter
from services.recommand_question import generate_faq

from datastore.factory import get_datastore, get_redis

from utils.schedulers import AsyncIOSchedulerWrapper

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
app.include_router(payment.router)
app.include_router(chat.router)

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()

    global cache
    cache = await get_redis()

    global i18n_adapter
    i18n_adapter = i18nAdapter("languages/local.json")

    scheduler = AsyncIOSchedulerWrapper()
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
