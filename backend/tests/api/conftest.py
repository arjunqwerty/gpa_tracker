"""API tests run against a real MongoDB database called gpa_tracker_test,
dropped and re-seeded before every test.

`client` is logged in as a freshly registered student; `anonymous` is not logged in."""
import os

os.environ["GPA_TRACKER_DB"] = "gpa_tracker_test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app import security  # noqa: E402
from app.database import DATABASE_NAME, MONGO_URL  # noqa: E402
from app.main import app  # noqa: E402
from tests.api.helpers import register  # noqa: E402


@pytest.fixture
def db():
    """Direct database access, for checking what is actually stored."""
    client = MongoClient(MONGO_URL)
    yield client[DATABASE_NAME]
    client.close()


@pytest.fixture
def anonymous(db):
    db.client.drop_database(DATABASE_NAME)
    security._recent_attempts.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(anonymous):
    register(anonymous, "student@example.com")
    return anonymous
