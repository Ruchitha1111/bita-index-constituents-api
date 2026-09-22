from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Ingestion(Base):
    __tablename__ = "ingestions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_ingestions_ingested_at", "ingested_at"),
    )