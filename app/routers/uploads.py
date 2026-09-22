import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import Ingestion
from app.models import Constituent


router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)

BATCH_SIZE = 500

REQUIRED_COLUMNS = {
    "index_code",
    "isin",
    "ticker",
    "name",
    "weight",
    "shares",
    "effective_date",
}


@router.post("/", status_code=201)
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        contents = file.file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(contents))

        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(
            set(reader.fieldnames)
        ):
            raise HTTPException(
                status_code=400,
                detail="CSV is missing one or more required columns",
            )

        ingestion = Ingestion(
            filename=file.filename,
            row_count=0,
        )

        db.add(ingestion)
        db.flush()

        batch = []
        row_count = 0

        for row_number, row in enumerate(reader, start=2):
            try:
                required_values = (
                    "index_code",
                    "isin",
                    "ticker",
                    "name",
                    "weight",
                    "shares",
                    "effective_date",
                )

                if any(not row[field].strip() for field in required_values):
                    raise ValueError(
                        "required fields must not be empty"
                    )

                constituent = Constituent(
                    ingestion_id=ingestion.id,
                    index_code=row["index_code"],
                    isin=row["isin"],
                    ticker=row["ticker"],
                    name=row["name"],
                    weight=float(row["weight"]),
                    shares=int(row["shares"]),
                    effective_date=date.fromisoformat(row["effective_date"]),
                )

                batch.append(constituent)
                row_count += 1

                if len(batch) >= BATCH_SIZE:
                    db.add_all(batch)
                    db.flush()
                    batch.clear()

            except (ValueError, TypeError, KeyError) as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid data in CSV row {row_number}: {exc}",
                )

        if batch:
            db.add_all(batch)
            db.flush()

        if row_count == 0:
            raise HTTPException(
                status_code=400,
                detail="CSV file is empty",
            )

        ingestion.row_count = row_count

        db.commit()

        return {
            "message": "File uploaded successfully",
            "ingestion_id": ingestion.id,
            "row_count": row_count,
        }

    except HTTPException:
        db.rollback()
        raise

    except UnicodeDecodeError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="CSV file must be UTF-8 encoded",
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to process CSV file",
        )