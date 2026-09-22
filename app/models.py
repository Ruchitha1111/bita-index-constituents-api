from datetime import date, datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String


class Base(DeclarativeBase):
    pass


class Constituent(Base):
    __tablename__ = "constituents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    ingestion_id: Mapped[int] = mapped_column(
        ForeignKey("ingestions.id"),
        nullable=False,
    )

    index_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    isin: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    ticker: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    weight: Mapped[float] = mapped_column(
        Numeric(12, 8),
        nullable=False,
    )

    shares: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_constituents_business_key",
            "index_code",
            "isin",
            "effective_date",
        ),
        Index(
            "ix_constituents_deleted_at",
            "deleted_at",
        ),
    )