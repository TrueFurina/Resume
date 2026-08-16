"""教室模型"""

from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
from app.models.database import Base
import enum


class ClassroomType(str, enum.Enum):
    LECTURE = "lecture"       # 普通教室
    LAB = "lab"              # 实验室
    COMPUTER = "computer"    # 机房
    MULTIMEDIA = "multimedia"  # 多媒体教室


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 教室名称，如 "物理楼201"
    building = Column(String(50), nullable=True)  # 所在楼栋
    capacity = Column(Integer, default=60)  # 容量
    room_type = Column(SAEnum(ClassroomType), default=ClassroomType.LECTURE)
    has_multimedia = Column(Boolean, default=True)
    is_lab = Column(Boolean, default=False)  # 是否为实验室
    is_active = Column(Boolean, default=True)
