"""教师模型"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.models.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    title = Column(String(50), default="讲师")  # 职称：教授/副教授/讲师/助教
    department = Column(String(100), default="物理系")
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    max_hours_per_week = Column(Integer, default=20)  # 周最大课时
    preferred_time_slots = Column(String(200), nullable=True)  # 偏好时间段，JSON 字符串
    is_active = Column(Boolean, default=True)

    sections = relationship("CourseSection", back_populates="teacher")
