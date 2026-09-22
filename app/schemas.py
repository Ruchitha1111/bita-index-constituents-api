from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ConstituentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    index_code: str
    isin: str
    ticker: str
    name: str
    weight: float
    shares: int
    effective_date: date
    ingested_at: datetime
    deleted_at: datetime | None


class DeleteResponse(BaseModel):
    message: str
    id: int