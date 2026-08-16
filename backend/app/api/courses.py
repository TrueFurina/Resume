"""课程管理 API"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.course import Course, CourseSection, CourseCategory, TermType
from app.models.teacher import Teacher

router = APIRouter()


# ---- Pydantic Schemas ----
class CourseCreate(BaseModel):
    code: str
    name: str
    category: CourseCategory = CourseCategory.THEORY
    credits: float = 1.0
    total_hours: int = 32
    lecture_hours: int = 24
    experiment_hours: int = 8
    max_students: int = 60
    department: str = "物理系"
    description: Optional[str] = None
    year: int = 2026
    term: TermType = TermType.AUTUMN


class SectionCreate(BaseModel):
    course_id: int
    section_name: str
    teacher_id: Optional[int] = None
    max_students: int = 60


class SectionResponse(BaseModel):
    id: int
    course_id: int
    section_name: str
    teacher_id: Optional[int]
    teacher_name: Optional[str] = None
    max_students: int
    enrolled_count: int

    class Config:
        from_attributes = True


class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    credits: float
    total_hours: int
    max_students: int
    department: str
    year: int
    term: str
    sections: List[SectionResponse] = []

    class Config:
        from_attributes = True


# ---- API 端点 ----
@router.get("/", response_model=List[CourseResponse])
def list_courses(
    department: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Course)
    if department:
        query = query.filter(Course.department == department)
    if year:
        query = query.filter(Course.year == year)
    return query.all()


@router.post("/", response_model=CourseResponse, status_code=201)
def create_course(req: CourseCreate, db: Session = Depends(get_db)):
    existing = db.query(Course).filter(Course.code == req.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="课程编号已存在")
    course = Course(**req.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


@router.post("/sections", response_model=SectionResponse, status_code=201)
def create_section(req: SectionCreate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == req.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    section = CourseSection(**req.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.get("/sections/{section_id}", response_model=SectionResponse)
def get_section(section_id: int, db: Session = Depends(get_db)):
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    return section
