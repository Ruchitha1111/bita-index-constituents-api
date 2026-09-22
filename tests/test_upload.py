from pathlib import Path

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.ingestion import Ingestion
from app.main import app
from app.models import Constituent


client = TestClient(app)


def test_upload_csv():
    csv_path = Path("data/index_constituents_sample.csv")

    with csv_path.open("rb") as file:
        response = client.post(
            "/uploads/",
            files={
                "file": (
                    "index_constituents_sample.csv",
                    file,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["message"] == "File uploaded successfully"
    assert data["row_count"] == 54
    assert "ingestion_id" in data


def test_upload_csv_twice_preserves_history():
    csv_path = Path("data/index_constituents_sample.csv")

    for _ in range(2):
        with csv_path.open("rb") as file:
            response = client.post(
                "/uploads/",
                files={
                    "file": (
                        "index_constituents_sample.csv",
                        file,
                        "text/csv",
                    )
                },
            )

        assert response.status_code == 201

    db = SessionLocal()

    try:
        assert db.query(Constituent).count() == 108
        assert db.query(Ingestion).count() == 2
    finally:
        db.close()


def test_delete_constituent_soft_deletes_row():
    csv_path = Path("data/index_constituents_sample.csv")

    with csv_path.open("rb") as file:
        upload_response = client.post(
            "/uploads/",
            files={
                "file": (
                    "index_constituents_sample.csv",
                    file,
                    "text/csv",
                )
            },
        )

    assert upload_response.status_code == 201

    db = SessionLocal()

    try:
        constituent = db.query(Constituent).first()
        constituent_id = constituent.id
    finally:
        db.close()

    delete_response = client.delete(
        f"/constituents/{constituent_id}"
    )

    assert delete_response.status_code == 200

    db = SessionLocal()

    try:
        deleted_constituent = (
            db.query(Constituent)
            .filter(Constituent.id == constituent_id)
            .first()
        )

        assert deleted_constituent is not None
        assert deleted_constituent.deleted_at is not None
    finally:
        db.close()

    get_response = client.get("/constituents/")

    assert get_response.status_code == 200

    returned_ids = {
        item["id"] for item in get_response.json()
    }

    assert constituent_id not in returned_ids


def test_export_rejects_invalid_date_range():
    response = client.get(
        "/constituents/export",
        params={
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
            "format": "json",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_date must be before or equal to end_date"
    )


def test_export_json_returns_constituents():
    csv_path = Path("data/index_constituents_sample.csv")

    with csv_path.open("rb") as file:
        upload_response = client.post(
            "/uploads/",
            files={
                "file": (
                    "index_constituents_sample.csv",
                    file,
                    "text/csv",
                )
            },
        )

    assert upload_response.status_code == 201

    response = client.get(
        "/constituents/export",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "format": "json",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 54
    assert data[0]["index_code"]
    assert data[0]["isin"]
    assert data[0]["effective_date"]


def test_export_csv_returns_csv_file():
    csv_path = Path("data/index_constituents_sample.csv")

    with csv_path.open("rb") as file:
        upload_response = client.post(
            "/uploads/",
            files={
                "file": (
                    "index_constituents_sample.csv",
                    file,
                    "text/csv",
                )
            },
        )

    assert upload_response.status_code == 201

    response = client.get(
        "/constituents/export",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "format": "csv",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    csv_content = response.text

    assert "index_code" in csv_content
    assert "isin" in csv_content
    assert "effective_date" in csv_content
    
def test_invalid_upload_rolls_back_transaction():
    csv_path = Path("data/invalid.csv")

    with csv_path.open("rb") as file:
        response = client.post(
            "/uploads/",
            files={
                "file": (
                    "invalid.csv",
                    file,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 400

    db = SessionLocal()

    try:
        assert db.query(Constituent).count() == 0
        assert db.query(Ingestion).count() == 0
    finally:
        db.close()
        
def test_upload_rejects_empty_required_field():
    csv_content = """index_code,isin,ticker,name,weight,shares,effective_date
BITA,,TEST,Test Company,10.5,1000,2026-01-02
"""

    response = client.post(
        "/uploads/",
        files={
            "file": (
                "empty_field.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid data in CSV row 2: required fields must not be empty"
    )
    
def test_delete_latest_version_does_not_restore_previous_version():
    csv_path = Path("data/index_constituents_sample.csv")

    for _ in range(2):
        with csv_path.open("rb") as file:
            response = client.post(
                "/uploads/",
                files={
                    "file": (
                        "index_constituents_sample.csv",
                        file,
                        "text/csv",
                    )
                },
            )

        assert response.status_code == 201

    db = SessionLocal()

    try:
        latest_constituent = (
            db.query(Constituent)
            .order_by(Constituent.id.desc())
            .first()
        )

        constituent_id = latest_constituent.id
    finally:
        db.close()

    delete_response = client.delete(
        f"/constituents/{constituent_id}"
    )

    assert delete_response.status_code == 200

    response = client.get("/constituents/")

    assert response.status_code == 200
    assert len(response.json()) == 53

    returned_ids = {
        item["id"] for item in response.json()
    }

    assert constituent_id not in returned_ids