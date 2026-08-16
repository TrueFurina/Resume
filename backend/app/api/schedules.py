"""排课管理 API"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.models.database import get_db
from app.models.schedule import ScheduleSlot, Weekday, TimeSlot, Enrollment
from app.models.course import CourseSection
from app.engine.scheduler import SchedulerEngine

router = APIRouter()


class ScheduleSlotCreate(BaseModel):
    section_id: int
    classroom_id: int
    weekday: Weekday
    time_slot: TimeSlot
    week_start: int = 1
    week_end: int = 18


class ScheduleSlotResponse(BaseModel):
    id: int
    section_id: int
    classroom_id: Optional[int]
    classroom_name: Optional[str] = None
    weekday: str
    time_slot: str
    week_start: int
    week_end: int

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    student_id: int
    section_id: int


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    section_id: int
    status: str

    class Config:
        from_attributes = True


class ScheduleRequest(BaseModel):
    """自动排课请求"""
    semester: str = "2026-2027-1"
    max_iterations: int = 1000


@router.post("/auto", summary="自动排课")
def auto_schedule(req: ScheduleRequest, db: Session = Depends(get_db)):
    """使用约束求解器自动生成课表"""
    engine = SchedulerEngine(db)
    result = engine.solve(max_iterations=req.max_iterations)
    return result


@router.post("/slots", response_model=ScheduleSlotResponse, status_code=201)
def create_slot(req: ScheduleSlotCreate, db: Session = Depends(get_db)):
    """手动添加排课时间段"""
    slot = ScheduleSlot(**req.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/slots", response_model=List[ScheduleSlotResponse])
def list_slots(section_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(ScheduleSlot)
    if section_id:
        query = query.filter(ScheduleSlot.section_id == section_id)
    return query.all()


@router.get("/timetable/{teacher_id}", summary="查看教师课表")
def get_teacher_timetable(teacher_id: int, db: Session = Depends(get_db)):
    """查询某位教师的完整课表"""
    sections = db.query(CourseSection).filter(
        CourseSection.teacher_id == teacher_id
    ).all()
    result = []
    for sec in sections:
        slots = db.query(ScheduleSlot).filter(
            ScheduleSlot.section_id == sec.id
        ).all()
        for s in slots:
            result.append({
                "section_id": sec.id,
                "section_name": sec.section_name,
                "course_name": sec.course.name if sec.course else "",
                "weekday": s.weekday.value,
                "time_slot": s.time_slot.value,
                "weeks": f"{s.week_start}-{s.week_end}周",
            })
    return result


# ---- 选课 ----
@router.post("/enroll", response_model=EnrollmentResponse)
def enroll(req: EnrollmentCreate, db: Session = Depends(get_db)):
    """学生选课"""
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == req.student_id,
        Enrollment.section_id == req.section_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已选过此课程")

    section = db.query(CourseSection).filter(
        CourseSection.id == req.section_id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    if section.enrolled_count >= section.max_students:
        raise HTTPException(status_code=400, detail="该教学班已满")

    enrollment = Enrollment(**req.model_dump())
    section.enrolled_count += 1
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.get("/enrollments/{student_id}", response_model=List[EnrollmentResponse])
def list_enrollments(student_id: int, db: Session = Depends(get_db)):
    return db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
