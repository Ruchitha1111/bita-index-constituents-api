import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion import Ingestion
from app.models import Base

load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD environment variable is not set")


DATABASE_URL = (
    f"postgresql+psycopg://postgres:{quote_plus(DB_PASSWORD)}"
    "@localhost:5432/bita_index"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()