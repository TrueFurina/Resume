"""排课模型 - 排课时间段、选课记录"""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship
from app.models.database import Base
import enum


class Weekday(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimeSlot(str, enum.Enum):
    """时间段"""
    MORNING_1 = "08:00-08:45"
    MORNING_2 = "08:55-09:40"
    MORNING_3 = "10:00-10:45"
    MORNING_4 = "10:55-11:40"
    AFTERNOON_1 = "14:00-14:45"
    AFTERNOON_2 = "14:55-15:40"
    AFTERNOON_3 = "16:00-16:45"
    AFTERNOON_4 = "16:55-17:40"
    EVENING_1 = "19:00-19:45"
    EVENING_2 = "19:55-20:40"


class ScheduleSlot(Base):
    """排课时间段 - 确定某课程在某时间某教室"""
    __tablename__ = "schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("course_sections.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    weekday = Column(SAEnum(Weekday), nullable=False)
    time_slot = Column(SAEnum(TimeSlot), nullable=False)
    week_start = Column(Integer, default=1)  # 起始周
    week_end = Column(Integer, default=18)   # 结束周
    is_odd_week = Column(Boolean, nullable=True)  # None=每周, True=单周, False=双周

    section = relationship("CourseSection", back_populates="schedule_slots")
    classroom = relationship("Classroom")


class Enrollment(Base):
    """选课记录"""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("course_sections.id"), nullable=False)
    status = Column(String(20), default="enrolled")  # enrolled / dropped / completed

    student = relationship("User")
    section = relationship("CourseSection")
