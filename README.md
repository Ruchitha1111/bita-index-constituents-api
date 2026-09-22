# BITA Index Constituents API

A FastAPI application for ingesting, storing, and serving historical index constituent data using PostgreSQL.

The API is designed to preserve ingestion history, prevent previously loaded data from being overwritten, support soft deletion, and export effective constituent data for a requested date range.

## Features

- Upload index constituent data through a CSV endpoint.
- Store every ingestion separately.
- Preserve all previously ingested rows.
- Resolve the current version of a constituent using the latest ingestion.
- Soft-delete constituent records without physically removing them from the database.
- Export constituent data as JSON or CSV.
- Validate CSV structure and row values.
- Roll back an entire upload when invalid data is encountered.
- PostgreSQL indexes for commonly queried fields.
- Automated tests covering the main functional requirements.

## Technology Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- Pytest
- Uvicorn

## Prerequisites

Before running the application, make sure you have the following installed:

- Python 3.11 or later
- PostgreSQL
- Git

The application uses a local PostgreSQL database named:

bita_index

The expected PostgreSQL connection is:

localhost:5432

## Installation

Clone the repository:

    git clone https://github.com/Ruchitha1111/bita-index-constituents-api.git

Move into the project directory:

    cd bita-index-constituents-api

Create a Python virtual environment:

    py -3.11 -m venv .venv

Activate the virtual environment in Windows PowerShell:

    .venv\Scripts\Activate.ps1

Install the required dependencies:

    pip install -r requirements.txt

## Environment Configuration

Create a file named `.env` in the project root.

Add your PostgreSQL password:

    DB_PASSWORD=your_postgres_password

The `.env` file is intentionally excluded from Git because it contains sensitive database credentials.

A safe example configuration is provided in `.env.example`.

## Database Setup

Create a PostgreSQL database named:

    bita_index

The application connects to PostgreSQL using:

    localhost:5432

The PostgreSQL username is:

    postgres

When the application starts, SQLAlchemy creates the required database tables if they do not already exist.

## Running the Application

Start the API with:

    uvicorn app.main:app --reload

The API will be available at:

    http://127.0.0.1:8000

Interactive Swagger documentation is available at:

    http://127.0.0.1:8000/docs

## Project Structure

    bita-index-constituents-api/
    |
    +-- app/
    |   +-- routers/
    |   |   +-- constituents.py
    |   |   +-- uploads.py
    |   |
    |   +-- database.py
    |   +-- ingestion.py
    |   +-- main.py
    |   +-- models.py
    |   +-- schemas.py
    |
    +-- data/
    |   +-- index_constituents_sample.csv
    |   +-- invalid.csv
    |
    +-- tests/
    |   +-- conftest.py
    |   +-- test_health.py
    |   +-- test_upload.py
    |
    +-- .env.example
    +-- .gitignore
    +-- requirements.txt
    +-- README.md

## API Endpoints

### Health Check

GET /constituents/health

Example response:

    {
        "status": "ok"
    }

### Upload CSV

POST /uploads/

The endpoint accepts a CSV file using multipart form data.

Required CSV columns:

    index_code
    isin
    ticker
    name
    weight
    shares
    effective_date

Example CSV row:

    index_code,isin,ticker,name,weight,shares,effective_date
    BITA-TECH50,US5949181045,MSFT,Microsoft Corporation,5.25,1000000,2026-07-01

Example response:

    {
        "message": "File uploaded successfully",
        "ingestion_id": 1,
        "row_count": 54
    }

### Get Current Constituents

GET /constituents/

The endpoint returns the latest ingested version for each business key:

    index_code + isin + effective_date

Soft-deleted records are excluded from the response.

### Soft Delete a Constituent

DELETE /constituents/{constituent_id}

The database row is not physically deleted.

Instead, the `deleted_at` field is populated with the deletion timestamp.

Deleted records are excluded from normal API results and exports while remaining available in the database.

Example response:

    {
        "message": "Constituent deleted successfully",
        "id": 123
    }

### Export Constituents

GET /constituents/export

Required query parameters:

    start_date
    end_date

Optional query parameter:

    format=json

or:

    format=csv

Example JSON export:

    /constituents/export?start_date=2026-01-01&end_date=2026-12-31&format=json

Example CSV export:

    /constituents/export?start_date=2026-01-01&end_date=2026-12-31&format=csv

The API rejects requests where `start_date` is later than `end_date`.

## Data Model

### Constituent

Each uploaded CSV row is stored as a separate constituent record.

Important fields include:

- `id` - database identifier
- `ingestion_id` - identifies the upload that created the row
- `index_code`
- `isin`
- `ticker`
- `name`
- `weight`
- `shares`
- `effective_date`
- `ingested_at`
- `deleted_at`

### Ingestion

Each CSV upload creates an ingestion record containing:

- `id`
- `filename`
- `ingested_at`
- `row_count`

This provides a record of each ingestion and allows uploaded data to be associated with a specific load.

## Handling Multiple Ingestions

The business key for a constituent is:

    index_code + isin + effective_date

The same business key may appear in multiple uploads.

The system therefore does not enforce uniqueness on this combination.

Every upload creates new database rows, preserving previous versions instead of overwriting them.

When API results are requested, the application selects the latest ingested version for each business key.

This allows repeated uploads while preserving the complete ingestion history.

## Deletion Strategy

The API uses soft deletion.

When a constituent is deleted:

    deleted_at = current timestamp

The original database row remains available.

Normal API results and exports exclude records where `deleted_at` is populated.

This approach was selected because the assessment requires deleted rows to remain recoverable and explicitly states that the database row should not actually be removed.

## Transaction and Error Handling

CSV uploads are processed inside a database transaction.

If an invalid row is encountered, the transaction is rolled back.

This prevents a partially processed CSV from leaving inconsistent data in the database.

The API validates:

- Required CSV columns
- Empty required fields
- Numeric values
- Dates
- Empty CSV files
- Export date ranges

Invalid requests return appropriate HTTP error responses.

## Batch Insertion

CSV rows are accumulated into batches before being added to the SQLAlchemy session.

The current batch size is:

    BATCH_SIZE = 500

This reduces the overhead of processing every row individually while keeping the insertion process manageable for larger CSV files.

The implementation intentionally does not use PostgreSQL `COPY` or native PostgreSQL bulk import because the assessment explicitly prohibits those mechanisms.

## Database Indexes

The following indexes are defined.

### Constituents

Business-key index:

    ix_constituents_business_key
    (index_code, isin, effective_date)

This supports queries involving the constituent business key.

Soft-deletion index:

    ix_constituents_deleted_at
    (deleted_at)

This supports filtering active and deleted records.

### Ingestions

Ingestion timestamp index:

    ix_ingestions_ingested_at
    (ingested_at)

This supports queries involving ingestion timestamps.

## Design Decisions

### FastAPI

FastAPI was selected because it provides:

- Request and response validation
- Automatic OpenAPI documentation
- Dependency injection
- Straightforward file upload support
- Type hints throughout the API

### SQLAlchemy

SQLAlchemy was selected as the database access layer because it provides:

- ORM-based database models
- PostgreSQL support
- Transaction management
- Parameterized database operations
- A clear separation between database models and API schemas

### Python CSV Module

Python's built-in `csv` module is used for CSV ingestion rather than pandas.

The input format is straightforward and does not require pandas-specific data-processing functionality. Using the standard library avoids unnecessary overhead and dependencies for the ingestion path.

### Why Not PostgreSQL COPY?

PostgreSQL `COPY` would normally be an efficient option for large CSV imports.

However, it was not used because the assessment explicitly prohibits `COPY` and native PostgreSQL bulk import mechanisms.

### Why Not Hard Delete?

Hard deletion was rejected because deleted records must remain recoverable and must not actually be removed from the database.

Soft deletion using `deleted_at` preserves the original database record while excluding it from normal API results.

### Why No Unique Constraint on the Business Key?

A unique constraint on:

    index_code + isin + effective_date

would prevent the same business key from appearing in multiple ingestion batches.

Because repeated uploads must preserve ingestion history, uniqueness is not enforced on this combination.

Instead, the application determines which version should be returned based on the latest ingestion.

## Testing

Run the complete test suite with:

    pytest

The test suite covers:

- Health endpoint
- CSV upload
- Repeated CSV uploads
- Preservation of ingestion history
- Soft deletion
- Invalid deletion requests
- Invalid date ranges
- JSON export
- CSV export
- Invalid CSV rollback
- Missing required values
- Latest-version deletion behavior

## Current Test Result

The current test suite contains 10 tests.

    10 passed

## Future Improvements

Possible improvements for a production-scale implementation include:

- Streaming CSV parsing for very large uploads
- Pagination for constituent retrieval
- Authentication and authorization
- Structured application logging
- Database migrations using Alembic
- More granular ingestion status and error tracking
- Additional database-level constraints where appropriate
- Integration tests against an isolated PostgreSQL test database