import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.ingestion import Ingestion
from app.main import app
from app.models import Constituent


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database():
    yield

    db = SessionLocal()

    try:
        db.query(Constituent).delete()
        db.query(Ingestion).delete()
        db.commit()
    finally:
        db.close()