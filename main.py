from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Header,Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import os
import cloudinary.uploader
from typing import Optional

from database import Base, engine, SessionLocal
from models import Student, Attendance, Admin
from schemas import StudentCreate, StudentResponse, AttendanceOut, AdminLogin, MarkAttendance
from auth import create_access_token, verify_password, get_password_hash
from dotenv import load_dotenv

# ----------------- Load environment variables -----------------
load_dotenv()

MARK_ABSENT_API_KEY = os.getenv("MARK_ABSENT_API_KEY")

# ----------------- Configure Cloudinary -----------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------- Initialize FastAPI -----------------
app = FastAPI(title="College Admin Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Dependency -----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- API Key Verification -----------------
def verify_api_key(api_key: str = Header(...)):
    if api_key != MARK_ABSENT_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ----------------- Auth APIs -----------------
@app.post("/auth/login")
def login(data: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.user_id == data.userId.lower()).first()
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": admin.user_id})
    return {"token": token}

@app.post("/auth/verify-answers")
def verify_answers(userId: str = Form(...), answer1: str = Form(...), answer2: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.user_id == userId.lower()).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if admin.answer1 != answer1 or admin.answer2 != answer2:
        raise HTTPException(status_code=400, detail="Wrong answers")
    return {"ok": True}

@app.post("/auth/reset-password")
def reset_password(userId: str = Form(...), newPassword: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.user_id == userId.lower()).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    admin.password_hash = get_password_hash(newPassword)
    db.commit()
    return {"ok": True}


# ----------------- Student APIs -----------------
@app.post("/students/", response_model=StudentResponse)
async def create_student(
    roll: str = Form(...),
    name: str = Form(...),
    branch: str = Form(...),
    dob: date = Form(...),
    issue_valid: str = Form(...),
    pin: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    roll = roll.upper()
    name = " ".join(word.capitalize() for word in name.split())
    db_student = db.query(Student).filter(Student.roll == roll).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Roll number already exists")
    if photo:
        upload_result = cloudinary.uploader.upload(photo.file, folder="students")
        photo_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")
    else:
        photo_url = None
        public_id = None
    new_student = Student(
        roll=roll,
        name=name,
        branch=branch,
        dob=dob,
        issue_valid=issue_valid,
        pin=get_password_hash(pin),
        photo=photo_url,
        photo_public_id=public_id
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


@app.get("/students", response_model=list[StudentResponse])
def list_students(
    name: str = Query(None),
    branch: str = Query(None),
    dob: str = Query(None),
    roll: str = Query(None),
    lastYears: int = Query(None),
    page: int = 1,
    pageSize: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Student)
    if name:
        q = q.filter(Student.name.ilike(f"%{name}%"))
    if branch:
        q = q.filter(Student.branch == branch)
    if dob:
        dob_dt = datetime.strptime(dob, "%Y-%m-%d").date()
        q = q.filter(Student.dob == dob_dt)
    if roll:
        q = q.filter(Student.roll == roll.upper())
    if lastYears:
        cutoff = date.today() - timedelta(days=365 * lastYears)
        q = q.filter(Student.issue_date >= cutoff)
    students = q.offset((page - 1) * pageSize).limit(pageSize).all()
    return students
# ---------------------------------get student detail--------------------
@app.get("/students/{roll}", response_model=StudentResponse)
def get_student(roll: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.roll == roll.upper()).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    return s
# --------------------update jstudent deetal-----------------
@app.put("/students/{roll}", response_model=StudentResponse)
def update_student(
    roll: str,
    name: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    issue_valid: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    pin: Optional[str] = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    s = db.query(Student).filter(Student.roll == roll.upper()).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    # ---------------- Upload photo to Cloudinary ----------------
    if photo:
        # Delete old photo if exists
        if s.photo_public_id:
            try:
                cloudinary.uploader.destroy(s.photo_public_id)
            except Exception as e:
                print(f"Failed to delete old image: {e}")

        # Upload new photo
        upload_result = cloudinary.uploader.upload(photo.file, folder="students")
        s.photo = upload_result.get("secure_url")
        s.photo_public_id = upload_result.get("public_id")

    # ---------------- Update other fields ----------------
    if name is not None and name.strip() != "":
        s.name = " ".join(word.capitalize() for word in name.split())

    if dob is not None and dob.strip() != "":
        s.dob = datetime.strptime(dob, "%Y-%m-%d").date()

    if issue_valid is not None and issue_valid.strip() != "":
        s.issue_valid = issue_valid

    if branch is not None and branch.strip() != "":
        s.branch = branch

    if pin is not None and pin.strip() != "":
        if len(pin) != 4 or not pin.isdigit():
            raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
        s.pin = get_password_hash(pin)

    db.commit()
    db.refresh(s)
    return s

# ----------------- Attendance APIs -----------------
@app.post("/attendance/mark")
def mark_attendance(attendance_data: MarkAttendance, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.roll == attendance_data.roll).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    today = date.today()
    if attendance_data.date != today:
        raise HTTPException(status_code=400, detail="Invalid date")
    record = db.query(Attendance).filter(Attendance.roll == attendance_data.roll, Attendance.date == today).first()
    if record:
        return {"message": "Attendance already marked"}
    new_record = Attendance(roll=attendance_data.roll, date=today, status="Present")
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"message": "Attendance marked as Present"}

@app.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(
    roll: str = Query(...),
    status: Optional[str] = Query(None),
    from_date: str = Query(None),
    to_date: str = Query(None),
    orderBy: str = Query(None),
    db: Session = Depends(get_db)
):
    today = date.today()
    default_start = date(today.year - 1, today.month, 1)
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else default_start
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else today
    q = db.query(Attendance).filter(Attendance.roll == roll.upper(), Attendance.date >= from_dt, Attendance.date <= to_dt)
    if status:
        q = q.filter(Attendance.status.ilike(f"%{status}%"))
    if orderBy == "roll":
        q = q.order_by(Attendance.roll)
    elif orderBy == "date":
        q = q.order_by(Attendance.date)
    return q.all()


# ----------------- Secure Scheduled Tasks APIs -----------------
@app.post("/tasks/mark-absent")
async def api_mark_absent_students(
    request: Request,
    mark_absent_api_key: str = Header(...),
    db: Session = Depends(get_db)
):

    verify_api_key(mark_absent_api_key)

    today = date.today()
    students = db.query(Student).all()
    for student in students:
        record = db.query(Attendance).filter(Attendance.roll == student.roll, Attendance.date == today).first()
        if not record:
            absent_record = Attendance(roll=student.roll, date=today, status="Absent")
            db.add(absent_record)
    db.commit()

    return {"message": "Absent students marked"}


@app.post("/tasks/delete-expired-students")
async def api_delete_expired_students(
        request: Request,
        mark_absent_api_key: str = Header(None),
        db: Session = Depends(get_db)
):
    # Verify API key
    verify_api_key(mark_absent_api_key)

    today = datetime.today()
    deleted_count = 0

    # Fetch students with valid issue_valid
    students = db.query(Student).filter(Student.issue_valid != None).all()

    for student in students:
        try:
            end_year_part = student.issue_valid.split("-")[1]
            end_year = int(end_year_part)
            if end_year < 100:
                end_year += 2000

            expire_date = datetime(end_year, 12, 31)

            if today > expire_date:
                # Delete student's attendance records
                db.query(Attendance).filter(Attendance.roll == student.roll).delete()
                # Delete student record
                db.delete(student)
                deleted_count += 1

        except Exception as e:
            print(f"Error deleting student {student.roll}: {e}")

    db.commit()

    return {"message": f"{deleted_count} expired students deleted"}


@app.post("/tasks/cleanup-old-attendance")
async def api_cleanup_old_attendance(
    request: Request,
    mark_absent_api_key: str = Header(None),
    db: Session = Depends(get_db)
):
    verify_api_key(mark_absent_api_key)

    today = datetime.today()
    cutoff_date = today - timedelta(days=365)
    deleted_count = db.query(Attendance).filter(Attendance.date < cutoff_date.date()).delete()
    db.commit()

    return {"message": f"{deleted_count} old attendance records deleted"}


# ----------------- Root -----------------
@app.get("/")
def read_root():
    return {"message": "College Admin Backend running."}


# ----------------- Database Setup -----------------
Base.metadata.create_all(bind=engine)