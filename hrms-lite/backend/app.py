import re
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from psycopg2 import IntegrityError, errorcodes

from database import get_db_cursor, init_db


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "frontend" / "static"
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_STATUSES = {"Present", "Absent"}


class EmployeeCreate(BaseModel):
    employeeId: str
    fullName: str
    email: str
    department: str


class AttendanceCreate(BaseModel):
    employeeId: str
    date: str
    status: str


app = FastAPI(title="HRMS Lite API", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup_event():
    init_db()


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request payload"})


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard():
    today = date.today()
    with get_db_cursor() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS count FROM employees")
        employee_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) AS count FROM attendance")
        total_attendance = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = %s AND status = 'Present'",
            (today,),
        )
        today_present = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = %s AND status = 'Absent'",
            (today,),
        )
        today_absent = cursor.fetchone()["count"]

    return {
        "employeeCount": employee_count,
        "totalAttendanceRecords": total_attendance,
        "today": today.isoformat(),
        "attendanceToday": {"present": today_present, "absent": today_absent},
    }


@app.get("/api/employees")
def get_employees():
    with get_db_cursor() as (_, cursor):
        cursor.execute(
            """
            SELECT
                e.employee_id,
                e.full_name,
                e.email,
                e.department,
                COALESCE(SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END), 0) AS present_days
            FROM employees e
            LEFT JOIN attendance a ON a.employee_id = e.employee_id
            GROUP BY e.employee_id, e.full_name, e.email, e.department
            ORDER BY e.created_at DESC
            """
        )
        rows = cursor.fetchall()
    employees = [
        {
            "employeeId": str(row["employee_id"]),
            "fullName": row["full_name"],
            "email": row["email"],
            "department": row["department"],
            "presentDays": row["present_days"],
        }
        for row in rows
    ]
    return {"employees": employees}


@app.post("/api/employees", status_code=201)
def create_employee(payload: EmployeeCreate):
    employee_id = payload.employeeId.strip()
    full_name = payload.fullName.strip()
    email = payload.email.strip().lower()
    department = payload.department.strip()

    if not employee_id or not full_name or not email or not department:
        raise HTTPException(status_code=400, detail="All fields are required")
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        with get_db_cursor(commit=True) as (_, cursor):
            cursor.execute(
                """
                INSERT INTO employees (employee_id, full_name, email, department)
                VALUES (%s, %s, %s, %s)
                """,
                (employee_id, full_name, email, department),
            )
    except IntegrityError as exc:
        constraint = exc.diag.constraint_name or ""
        if exc.pgcode == errorcodes.UNIQUE_VIOLATION and "pkey" in constraint:
            raise HTTPException(status_code=409, detail="Employee ID already exists")
        if exc.pgcode == errorcodes.UNIQUE_VIOLATION and "email" in constraint:
            raise HTTPException(status_code=409, detail="Email already exists")
        raise HTTPException(status_code=409, detail="Duplicate employee data")

    return {"message": "Employee created successfully"}


@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: str):
    employee_id = employee_id.strip()
    if not employee_id:
        raise HTTPException(status_code=400, detail="Employee ID is required")

    with get_db_cursor(commit=True) as (_, cursor):
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = %s", (employee_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))

    return {"message": "Employee deleted successfully"}


@app.post("/api/attendance", status_code=201)
def create_attendance(payload: AttendanceCreate):
    employee_id = payload.employeeId.strip()
    attendance_date = payload.date.strip()
    status = payload.status.strip().title()

    if not employee_id or not attendance_date or not status:
        raise HTTPException(status_code=400, detail="employeeId, date and status are required")
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Status must be Present or Absent")
    if not DATE_REGEX.match(attendance_date):
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    try:
        attendance_day = datetime.strptime(attendance_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    with get_db_cursor(commit=True) as (_, cursor):
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = %s", (employee_id,))
        employee_exists = cursor.fetchone()
        if employee_exists is None:
            raise HTTPException(status_code=404, detail="Employee does not exist")

        try:
            cursor.execute(
                """
                INSERT INTO attendance (employee_id, attendance_date, status)
                VALUES (%s, %s, %s)
                """,
                (employee_id, attendance_day, status),
            )
        except IntegrityError as exc:
            if exc.pgcode != errorcodes.UNIQUE_VIOLATION:
                raise
            raise HTTPException(
                status_code=409,
                detail="Attendance already marked for this employee on this date",
            )

    return {"message": "Attendance marked successfully"}


@app.get("/api/attendance")
def get_attendance(date_filter: str | None = Query(default=None, alias="date")):
    query = """
        SELECT a.id, a.employee_id, e.full_name, a.attendance_date, a.status
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
    """
    params = []

    if date_filter:
        if not DATE_REGEX.match(date_filter):
            raise HTTPException(status_code=400, detail="date query must be in YYYY-MM-DD format")
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="date query must be in YYYY-MM-DD format"
            )
        query += " WHERE a.attendance_date = %s"
        params.append(parsed_date)

    query += " ORDER BY a.attendance_date DESC, e.full_name ASC"

    with get_db_cursor() as (_, cursor):
        cursor.execute(query, params)
        rows = cursor.fetchall()

    records = [
        {
            "id": row["id"],
            "employeeId": str(row["employee_id"]),
            "fullName": row["full_name"],
            "date": row["attendance_date"].isoformat(),
            "status": row["status"],
        }
        for row in rows
    ]
    return {"attendance": records}


@app.get("/api/employees/{employee_id}/attendance")
def get_employee_attendance(employee_id: str):
    with get_db_cursor() as (_, cursor):
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = %s", (employee_id,))
        employee = cursor.fetchone()
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found")

        cursor.execute(
            """
            SELECT id, employee_id, attendance_date, status
            FROM attendance
            WHERE employee_id = %s
            ORDER BY attendance_date DESC
            """,
            (employee_id,),
        )
        rows = cursor.fetchall()

    records = [
        {
            "id": row["id"],
            "employeeId": str(row["employee_id"]),
            "date": row["attendance_date"].isoformat(),
            "status": row["status"],
        }
        for row in rows
    ]
    return {"attendance": records}
