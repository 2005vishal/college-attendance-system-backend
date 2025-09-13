from datetime import date, timedelta
from typing import Iterable
from sqlalchemy import select, and_, or_, desc, asc
from sqlalchemy.orm import Session


from models import Student, Attendance, Admin
from auth import get_password_hash


# ===== Users =====


def create_user(db: Session, user_id: str, password: str, q1: str, q2: str, a1: str, a2: str) -> Admin:
    user = Admin(
    user_id=user_id,
    password_hash=get_password_hash(password),
    security_q1=q1,
    security_q2=q2,
    answer1=a1,
    answer2=a2,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ===== Students =====


def create_student(db: Session, s: Student) -> Student:
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update_student(db: Session, s: Student) -> Student:
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def delete_student(db: Session, roll: str) -> bool:
    s = db.query(Student).filter(Student.roll == roll).first()
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True


# Filters: lastYears uses issue_date cutoff


def list_students(
    db: Session,
    name: str | None,
    branch: str | None,
    dob: date | None,
    roll: str | None,
    last_years: int | None,
    page: int,
    page_size: int,
    ) -> Iterable[Student]:
    stmt = select(Student)
    conditions = []
    if name:
        conditions.append(Student.name.ilike(f"%{name}%"))
    if branch:
        conditions.append(Student.branch == branch)
    if dob:
        conditions.append(Student.dob == dob)
    if roll:
        conditions.append(Student.roll == roll)
    if last_years and last_years > 0:
        cutoff = date.today().replace(year=date.today().year - last_years)
        conditions.append(Student.issue_date >= cutoff)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Student.roll.asc()).limit(page_size).offset((page - 1) * page_size)
    return db.execute(stmt).scalars().all()

# ===== Attendance =====


def list_attendance(
    db: Session,
    dfrom: date,
    dto: date,
    roll: str | None,
    order_by: str | None,
    ):
    stmt = select(Attendance).where(and_(Attendance.date >= dfrom, Attendance.date <= dto))
    if roll:
        stmt = stmt.where(Attendance.roll == roll)
    if order_by == "roll":
        stmt = stmt.order_by(Attendance.roll.asc(), Attendance.date.asc())
    else:
        stmt = stmt.order_by(Attendance.date.asc(), Attendance.roll.asc())
    return db.execute(stmt).scalars().all()