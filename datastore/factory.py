from datastore.datastore import DataStore
from datastore.providers.redis_chat import RedisChat
import os


async def get_datastore() -> DataStore:
    from datastore.providers.qdrant_datastore import QdrantDataStore

    return QdrantDataStore()

async def get_redis() -> RedisChat:
    return RedisChat()