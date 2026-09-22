from fastapi import FastAPI

from app.database import engine
from app.ingestion import Ingestion
from app.models import Base
from app.routers.constituents import router as constituents_router
from app.routers.uploads import router as uploads_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="BITA Index Constituents API",
    version="1.0.0",
)

app.include_router(constituents_router)
app.include_router(uploads_router)