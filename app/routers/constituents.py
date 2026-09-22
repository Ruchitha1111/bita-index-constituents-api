import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Constituent
from app.schemas import ConstituentResponse, DeleteResponse


router = APIRouter(
    prefix="/constituents",
    tags=["Constituents"],
)


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/", response_model=list[ConstituentResponse])
def get_constituents(
    db: Session = Depends(get_db),
):
    latest_ingestion = (
        db.query(
            Constituent.index_code,
            Constituent.isin,
            Constituent.effective_date,
            func.max(Constituent.ingested_at).label("latest_ingested_at"),
        )
        .group_by(
            Constituent.index_code,
            Constituent.isin,
            Constituent.effective_date,
        )
        .subquery()
    )

    return (
        db.query(Constituent)
        .join(
            latest_ingestion,
            (
                (Constituent.index_code == latest_ingestion.c.index_code)
                & (Constituent.isin == latest_ingestion.c.isin)
                & (Constituent.effective_date == latest_ingestion.c.effective_date)
                & (Constituent.ingested_at == latest_ingestion.c.latest_ingested_at)
            ),
        )
        .filter(Constituent.deleted_at.is_(None))
        .all()
    )


@router.delete(
    "/{constituent_id}",
    response_model=DeleteResponse,
)
def delete_constituent(
    constituent_id: int,
    db: Session = Depends(get_db),
):
    constituent = (
        db.query(Constituent)
        .filter(Constituent.id == constituent_id)
        .first()
    )

    if constituent is None:
        raise HTTPException(
            status_code=404,
            detail="Constituent not found",
        )

    if constituent.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail="Constituent not found",
        )

    constituent.deleted_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Constituent deleted successfully",
        "id": constituent.id,
    }


@router.get("/export")
def export_constituents(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    latest_ingestion = (
        db.query(
            Constituent.index_code,
            Constituent.isin,
            Constituent.effective_date,
            func.max(Constituent.ingested_at).label("latest_ingested_at"),
        )
        .filter(
            Constituent.effective_date >= start_date,
            Constituent.effective_date <= end_date,
        )
        .group_by(
            Constituent.index_code,
            Constituent.isin,
            Constituent.effective_date,
        )
        .subquery()
    )

    constituents = (
        db.query(Constituent)
        .join(
            latest_ingestion,
            (
                (Constituent.index_code == latest_ingestion.c.index_code)
                & (Constituent.isin == latest_ingestion.c.isin)
                & (Constituent.effective_date == latest_ingestion.c.effective_date)
                & (Constituent.ingested_at == latest_ingestion.c.latest_ingested_at)
            ),
        )
        .filter(Constituent.deleted_at.is_(None))
        .all()
    )

    if format == "csv":
        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "id",
            "index_code",
            "isin",
            "ticker",
            "name",
            "weight",
            "shares",
            "effective_date",
            "ingested_at",
            "deleted_at",
        ])

        for constituent in constituents:
            writer.writerow([
                constituent.id,
                constituent.index_code,
                constituent.isin,
                constituent.ticker,
                constituent.name,
                constituent.weight,
                constituent.shares,
                constituent.effective_date,
                constituent.ingested_at,
                constituent.deleted_at,
            ])

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=constituents.csv"
            },
        )

    return constituents