"""MongoDB connection. Configure with the GPA_TRACKER_MONGO_URL and GPA_TRACKER_DB environment variables.

MongoDB must run as a replica set (even a single node) because some writes use transactions.
"""
import os
from contextlib import asynccontextmanager

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.models import ALL_DOCUMENTS

MONGO_URL = os.getenv("GPA_TRACKER_MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("GPA_TRACKER_DB", "gpa_tracker")

_client: AsyncMongoClient | None = None


async def connect():
    global _client
    _client = AsyncMongoClient(MONGO_URL, tz_aware=True)
    await init_beanie(database=_client[DATABASE_NAME], document_models=ALL_DOCUMENTS)


async def disconnect():
    await _client.close()


@asynccontextmanager
async def transaction():
    """Writes passed `session=session` inside this block are committed or rolled back together."""
    async with _client.start_session() as session:
        async with await session.start_transaction():
            yield session
