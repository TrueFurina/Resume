"""用户模型 - 管理员、教师、学生"""

from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
from app.models.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"      # 系统管理员
    TEACHER = "teacher"  # 教师
    STUDENT = "student"  # 学生


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
