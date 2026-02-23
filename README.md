# HRMS Lite Backend

FastAPI backend for HRMS Lite with PostgreSQL persistence.

## Tech Stack

- Python 3
- FastAPI
- Uvicorn
- PostgreSQL
- psycopg2

## Folder Structure

```text
backend/
  app.py
  database.py
  requirements.txt
  .env.example
```

## Environment Setup

1. Create PostgreSQL database:

```sql
CREATE DATABASE hrms_lite;
```

2. Create env file:

```bash
copy .env.example .env
```

3. Update `.env` if needed:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hrms_lite
```

## Install and Run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/employees`
- `POST /api/employees`
- `DELETE /api/employees/{employeeId}`
- `GET /api/attendance?date=YYYY-MM-DD`
- `GET /api/employees/{employeeId}/attendance`
- `POST /api/attendance`

## Notes

- Database schema is auto-created on app startup.
- Legacy static frontend is served at `http://localhost:8000`.
