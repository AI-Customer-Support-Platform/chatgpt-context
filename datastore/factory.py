from datastore.datastore import DataStore
import os


async def get_datastore() -> DataStore:
    from datastore.providers.qdrant_datastore import QdrantDataStore

    return QdrantDataStore()