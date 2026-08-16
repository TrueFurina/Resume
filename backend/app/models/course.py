"""课程模型"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.models.database import Base
import enum


class TermType(str, enum.Enum):
    SPRING = "spring"    # 春季学期
    AUTUMN = "autumn"    # 秋季学期


class CourseCategory(str, enum.Enum):
    THEORY = "theory"       # 理论课
    EXPERIMENT = "experiment"  # 实验课
    SEMINAR = "seminar"     # 研讨课
    PRACTICE = "practice"   # 实践课


class Course(Base):
    """课程基本信息"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # 课程编号
    name = Column(String(200), nullable=False)  # 课程名称
    category = Column(SAEnum(CourseCategory), default=CourseCategory.THEORY)
    credits = Column(Float, default=1.0)  # 学分
    total_hours = Column(Integer, default=32)  # 总学时
    lecture_hours = Column(Integer, default=24)  # 讲授学时
    experiment_hours = Column(Integer, default=8)  # 实验学时
    max_students = Column(Integer, default=60)  # 容量上限
    department = Column(String(100), default="物理系")  # 开课院系
    description = Column(String(500), nullable=True)
    year = Column(Integer, nullable=False)  # 学年
    term = Column(SAEnum(TermType), nullable=False)  # 学期

    # 关系
    sections = relationship("CourseSection", back_populates="course", cascade="all, delete-orphan")


class CourseSection(Base):
    """课程教学班 - 一门课可以分多个班"""
    __tablename__ = "course_sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    section_name = Column(String(50), nullable=False)  # 班级名称，如 "物理101-1班"
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    max_students = Column(Integer, default=60)
    enrolled_count = Column(Integer, default=0)

    course = relationship("Course", back_populates="sections")
    teacher = relationship("Teacher", back_populates="sections")
    schedule_slots = relationship("ScheduleSlot", back_populates="section", cascade="all, delete-orphan")
