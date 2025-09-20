# schemas.py
from pydantic import BaseModel
from datetime import date
from typing import Optional


# ----------------- Auth -----------------
class AdminLogin(BaseModel):
    userId: str
    password: str


# ----------------- Student -----------------

class StudentBase(BaseModel):
    roll: str
    name: str
    branch: str
    dob: date
    issue_valid: str
    pin: str
    photo: str   # ✅ now mandatory (no None, no default)

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    class Config:
        orm_mode = True


# ----------------- Attendance -----------------
class AttendanceBase(BaseModel):
    roll: str
    date: date
    time: str
    status: str


class AttendanceOut(AttendanceBase):
    class Config:
        orm_mode = True



class MarkAttendance(BaseModel):
    roll: str
    date: date
    time: str

