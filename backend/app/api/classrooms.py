"""教室管理 API"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.classroom import Classroom, ClassroomType

router = APIRouter()


class ClassroomCreate(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: int = 60
    room_type: ClassroomType = ClassroomType.LECTURE
    has_multimedia: bool = True
    is_lab: bool = False


class ClassroomResponse(BaseModel):
    id: int
    name: str
    building: Optional[str]
    capacity: int
    room_type: str
    has_multimedia: bool
    is_lab: bool
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ClassroomResponse])
def list_classrooms(
    room_type: Optional[ClassroomType] = None,
    min_capacity: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Classroom)
    if room_type:
        query = query.filter(Classroom.room_type == room_type)
    if min_capacity:
        query = query.filter(Classroom.capacity >= min_capacity)
    return query.all()


@router.post("/", response_model=ClassroomResponse, status_code=201)
def create_classroom(req: ClassroomCreate, db: Session = Depends(get_db)):
    existing = db.query(Classroom).filter(Classroom.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="教室名称已存在")
    classroom = Classroom(**req.model_dump())
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(classroom_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="教室不存在")
    return classroom
