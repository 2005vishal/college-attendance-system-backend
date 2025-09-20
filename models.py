# models.py
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, CHAR,Text
from sqlalchemy.orm import relationship
from database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    answer1 = Column(String, nullable=False)
    answer2 = Column(String, nullable=False)


class Student(Base):
    __tablename__ = 'students'

    roll = Column(String(20), primary_key=True)
    name = Column(String(100))
    branch = Column(String(50))
    dob = Column(Date)
    issue_valid = Column(String(20))
    pin = Column(Text, nullable=False)  # Store hashed pin here
    photo = Column(String(255))  # URL of the image
    photo_public_id = Column(String(255))  # Cloudinary public_id

    # Correct relationship property name
    attendances = relationship("Attendance", back_populates="student")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    roll = Column(String(20), ForeignKey("students.roll"), index=True)  # Added index
    date = Column(Date, nullable=False)
    time = Column(String(20), nullable=False)
    status = Column(String(10), nullable=False)

    student = relationship("Student", back_populates="attendances")



