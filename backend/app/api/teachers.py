"""教师管理 API"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.teacher import Teacher

router = APIRouter()


class TeacherCreate(BaseModel):
    name: str
    title: str = "讲师"
    department: str = "物理系"
    email: Optional[str] = None
    phone: Optional[str] = None
    max_hours_per_week: int = 20


class TeacherResponse(BaseModel):
    id: int
    name: str
    title: str
    department: str
    email: Optional[str]
    phone: Optional[str]
    max_hours_per_week: int
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TeacherResponse])
def list_teachers(department: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Teacher)
    if department:
        query = query.filter(Teacher.department == department)
    return query.all()


@router.post("/", response_model=TeacherResponse, status_code=201)
def create_teacher(req: TeacherCreate, db: Session = Depends(get_db)):
    teacher = Teacher(**req.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    return teacher
