"""约束求解器 - 核心排课算法

将排课问题建模为约束满足问题 (CSP):
- 变量: 每个教学班需要分配 (星期, 时间段, 教室)
- 域: 所有可用时间段 × 所有可用教室
- 约束:
  1. 同一教师不能在同一时间上两门课
  2. 同一教室不能在同一时间被两个班使用
  3. 教室容量 >= 选课人数
  4. 教师每周课时 <= max_hours_per_week
  5. 实验课必须在实验室上
"""

from typing import List, Dict, Tuple, Optional
from itertools import product

from sqlalchemy.orm import Session

from app.models.course import CourseSection, CourseCategory
from app.models.teacher import Teacher
from app.models.classroom import Classroom, ClassroomType
from app.models.schedule import ScheduleSlot, Weekday, TimeSlot


class SchedulerEngine:
    """排课约束求解器"""

    def __init__(self, db: Session):
        self.db = db
        # 所有可用时间段
        self.weekdays = list(Weekday)
        self.time_slots = list(TimeSlot)
        # 限制在工作日（周一到周五）
        self.weekdays = [d for d in self.weekdays if d.value not in ("saturday", "sunday")]

    def solve(self, max_iterations: int = 1000) -> dict:
        """执行排课求解"""
        sections = self.db.query(CourseSection).all()
        classrooms = self.db.query(Classroom).filter(Classroom.is_active == True).all()
        teachers = self.db.query(Teacher).filter(Teacher.is_active == True).all()

        if not sections:
            return {"success": False, "error": "没有需要排课的教学班"}
        if not classrooms:
            return {"success": False, "error": "没有可用的教室"}

        # 已分配的 (section_id, weekday, time_slot) -> classroom_id
        assigned = {}
        # 统计每位教师每周课时
        teacher_hours = {t.id: 0 for t in teachers}

        # 贪心 + 回溯
        solution = self._backtrack(sections, classrooms, teachers, assigned, teacher_hours, 0)

        if solution is None:
            return {"success": False, "error": "无法找到满足所有约束的排课方案，请检查教师课时和教室资源"}

        # 保存到数据库
        slots_created = 0
        for section_id, weekday, time_slot, classroom_id in solution:
            # 检查是否已有
            existing = self.db.query(ScheduleSlot).filter(
                ScheduleSlot.section_id == section_id,
                ScheduleSlot.weekday == weekday,
                ScheduleSlot.time_slot == time_slot,
            ).first()
            if not existing:
                slot = ScheduleSlot(
                    section_id=section_id,
                    classroom_id=classroom_id,
                    weekday=Weekday(weekday),
                    time_slot=TimeSlot(time_slot),
                    week_start=1,
                    week_end=18,
                )
                self.db.add(slot)
                slots_created += 1

        self.db.commit()

        return {
            "success": True,
            "total_sections": len(sections),
            "slots_created": slots_created,
        }

    def _backtrack(self, sections, classrooms, teachers, assigned, teacher_hours, idx):
        """回溯搜索"""
        if idx >= len(sections):
            # 所有教学班都已分配
            return []

        section = sections[idx]
        teacher_id = section.teacher_id

        # 为该教学班生成候选 (weekday, time_slot, classroom)
        candidates = []
        for wd in self.weekdays:
            for ts in self.time_slots:
                for cr in classrooms:
                    if self._check_constraints(section, wd, ts, cr, teacher_id,
                                                assigned, teacher_hours):
                        candidates.append((wd.value, ts.value, cr.id))

        # 按约束宽松度排序 - 优先分配约束紧的
        # 这里已按 sections 顺序递归，可以用 MRV 启发式优化
        for weekday_val, time_slot_val, classroom_id in candidates:
            # 分配
            assigned[(section.id, weekday_val, time_slot_val)] = classroom_id
            if teacher_id:
                teacher_hours[teacher_id] = teacher_hours.get(teacher_id, 0) + 1

            rest = self._backtrack(sections, classrooms, teachers,
                                   assigned, teacher_hours, idx + 1)
            if rest is not None:
                return [(section.id, weekday_val, time_slot_val, classroom_id)] + rest

            # 回溯
            del assigned[(section.id, weekday_val, time_slot_val)]
            if teacher_id:
                teacher_hours[teacher_id] = teacher_hours.get(teacher_id, 0) - 1

        return None  # 回溯

    def _check_constraints(self, section: CourseSection, weekday: Weekday,
                           time_slot: TimeSlot, classroom: Classroom,
                           teacher_id: Optional[int], assigned: Dict,
                           teacher_hours: Dict) -> bool:
        """检查所有约束"""
        key = (section.id, weekday.value, time_slot.value)

        # 约束 1: 同一教室不能在同一时间被两个班使用
        for (sid, wd, ts), cid in assigned.items():
            if wd == weekday.value and ts == time_slot.value and cid == classroom.id:
                return False
            # 约束 2: 同一教师不能在同一时间上两门课
            if teacher_id:
                other_section = self.db.query(CourseSection).filter(
                    CourseSection.id == sid
                ).first()
                if other_section and other_section.teacher_id == teacher_id:
                    if wd == weekday.value and ts == time_slot.value:
                        return False

        # 约束 3: 教室容量 >= 选课人数
        if classroom.capacity < section.max_students:
            return False

        # 约束 4: 教师每周课时限制
        if teacher_id and teacher_hours.get(teacher_id, 0) >= 20:
            return False

        # 约束 5: 实验课必须在实验室
        course = section.course
        if course and course.category == CourseCategory.EXPERIMENT:
            if not classroom.is_lab:
                return False

        return True
