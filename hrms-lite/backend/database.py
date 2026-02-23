import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hrms_lite"
)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@contextmanager
def get_db_cursor(commit: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_db():
    with get_db_cursor(commit=True) as (_, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id BIGSERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                attendance_date DATE NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
                UNIQUE (employee_id, attendance_date)
            )
            """
        )
