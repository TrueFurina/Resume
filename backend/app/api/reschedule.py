"""调课 API - 上传数据 + 查询空闲时段"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.utils.excel_parser import ScheduleDatabase
from app.agent.reschedule_agent import RescheduleAgent
from app.agent.student_schedule import StudentSchedule

router = APIRouter()

# 全局排课数据库 + 学生课表
_db = ScheduleDatabase()
_student = StudentSchedule()
_agent = RescheduleAgent(_db, student=_student)

# 默认实验安排表路径
DEFAULT_SCHEDULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "schedule.xlsx"
)


class ChatRequest(BaseModel):
    message: str


class ConsultRequest(BaseModel):
    """选课咨询 / 实验辅导请求"""
    question: str


class AdminLoginRequest(BaseModel):
    """管理员登录"""
    username: str
    password: str


class ConsultResponse(BaseModel):
    success: bool
    message: str
    reply: str = ""
    data: dict = {}


class ChatResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}


@router.post("/upload", summary="上传实验安排表 Excel")
async def upload_schedule(file: UploadFile = File(...)):
    """上传实验安排表 Excel 文件"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 格式的 Excel 文件")

    # 保存上传的文件
    save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", file.filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        _db.load_from_excel(save_path)
        return {
            "success": True,
            "message": f"✅ 成功加载 {len(_db.entries)} 条排课记录",
            "total_entries": len(_db.entries),
            "rooms": _db.get_all_rooms()[:10],
            "teachers": _db.get_all_teachers(),
            "week_range": list(_db.get_week_range()),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败：{str(e)}")


@router.post("/chat", response_model=ChatResponse, summary="教师调课咨询")
async def reschedule_chat(req: ChatRequest):
    """教师输入调课请求，返回可用时段"""
    if not req.message.strip():
        return ChatResponse(success=False, message="请输入调课请求")

    result = _agent.process_request(req.message)
    return ChatResponse(
        success=result["success"],
        message=result["message"],
        data={
            "target_week": result.get("target_week"),
            "available_slots": result.get("available_slots", []),
            "excluded_slots": result.get("excluded_slots", []),
            "ai_plans": result.get("ai_plans", []),
            "total": result.get("total", 0),
            "need_info": result.get("need_info", False),
            "followup_questions": result.get("followup_questions", []),
        },
    )


@router.get("/status", summary="查看系统状态")
async def get_status():
    """查看系统加载状态"""
    return {
        "loaded": _db.loaded,
        "total_entries": len(_db.entries) if _db.loaded else 0,
        "rooms": _db.get_all_rooms() if _db.loaded else [],
        "teachers": _db.get_all_teachers() if _db.loaded else [],
        "week_range": list(_db.get_week_range()) if _db.loaded else [],
    }


@router.post("/upload-student", summary="上传学生课表 Excel/PDF")
async def upload_student_schedule(file: UploadFile = File(...)):
    """上传学生课表文件
    - Excel（.xlsx/.xls）：表头 [课程名, 星期, 节次, 周次]
    - PDF（.pdf）：教务系统导出的课表，自动解析（尽力）
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.pdf')):
        raise HTTPException(status_code=400, detail="请上传 .xlsx / .xls / .pdf 格式的文件")

    save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"student_{file.filename}")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        if file.filename.lower().endswith('.pdf'):
            from app.utils.pdf_schedule_parser import PdfScheduleParser
            parser = PdfScheduleParser()
            courses = parser.parse(save_path)
            if not courses:
                raise ValueError("PDF 解析出 0 门课程，请确认是教务系统导出的课表")
            _student.name = os.path.splitext(file.filename)[0]
            _student.courses = courses
            count = len(courses)
        else:
            count = _student.load_from_excel(save_path)

        return {
            "success": True,
            "message": f"✅ 成功加载 {count} 门课程，已更新学生课表",
            "total_courses": count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败：{str(e)}")


@router.get("/student-status", summary="查看学生课表状态")
async def get_student_status():
    """查看学生课表信息"""
    return {
        "name": _student.name,
        "student_id": _student.student_id,
        "semester": _student.semester,
        "total_courses": len(_student.courses),
        "sample_courses": _student.courses[:5],
    }


@router.post("/load-default", summary="加载默认实验安排表")
async def load_default():
    """加载已有的 schedule.xlsx"""
    if os.path.exists(DEFAULT_SCHEDULE_PATH):
        _db.load_from_excel(DEFAULT_SCHEDULE_PATH)
        return {
            "success": True,
            "message": f"✅ 成功加载 {len(_db.entries)} 条排课记录",
            "total_entries": len(_db.entries),
        }
    raise HTTPException(status_code=404, detail="默认文件不存在，请先上传")


# 轻量知识源：从实验安排表提取实验项目信息（P1-3，不依赖外部文档）
def _build_knowledge_context() -> str:
    """从实验安排表提取实验项目知识（实验名/教室/教师/班级）"""
    if not _db.loaded:
        return ""
    experiments = set()
    rooms = set()
    teachers = set()
    for e in _db.entries:
        if e.experiment:
            experiments.add(e.experiment)
        if e.room:
            rooms.add(e.room)
        if e.teacher:
            teachers.add(e.teacher)
    context = (
        f"本系统实验安排表知识源：\n"
        f"- 实验项目（{len(experiments)}个）：{'、'.join(sorted(experiments)[:15])}\n"
        f"- 实验室（{len(rooms)}间）：{'、'.join(sorted(rooms)[:10])}\n"
        f"- 实验教师（{len(teachers)}位）：{'、'.join(sorted(teachers)[:10])}\n"
        f"- 涉及学生课表：{len(_student.students)}人（多学生课表）"
    )
    return context


@router.post("/course-select", response_model=ConsultResponse, summary="选课咨询（四大模块之一）")
async def course_select_consult(req: ConsultRequest):
    """选课咨询：LLM 回答选课资格/先修课程/学分要求等问题"""
    if not req.question.strip():
        return ConsultResponse(success=False, message="请输入问题")

    # 构建学生课表 + 实验知识源上下文
    context = (
        f"当前学生：{_student.name}（{_student.semester}），课表共 {len(_student.courses)} 门课程。\n"
        + _build_knowledge_context()
    )
    result = _agent.llm_parser.consult(req.question, context=context, role="course_select")

    if "error" in result:
        return ConsultResponse(success=False, message=result["error"])
    return ConsultResponse(success=True, message="选课咨询完成", reply=result.get("reply", ""))


@router.post("/experiment-tutor", response_model=ConsultResponse, summary="实验辅导（四大模块之一）")
async def experiment_tutor_consult(req: ConsultRequest):
    """实验辅导：LLM 回答实验原理/数据处理/误差分析/报告规范等问题"""
    if not req.question.strip():
        return ConsultResponse(success=False, message="请输入问题")

    # 实验辅导基于实验知识源上下文
    context = _build_knowledge_context()
    result = _agent.llm_parser.consult(req.question, context=context, role="experiment_tutor")

    if "error" in result:
        return ConsultResponse(success=False, message=result["error"])
    return ConsultResponse(success=True, message="实验辅导完成", reply=result.get("reply", ""))


# 管理员固定账号（演示用，生产可换数据库）
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"


@router.post("/admin-login", summary="管理员登录（审批台用）")
async def admin_login(req: AdminLoginRequest):
    """管理员登录校验（普通用户无需登录，仅审批台需要）"""
    if req.username == ADMIN_USER and req.password == ADMIN_PASS:
        return {"success": True, "message": "✅ 管理员登录成功", "role": "admin"}
    raise HTTPException(status_code=401, detail="用户名或密码错误")


@router.post("/auto-schedule", summary="排课自动生成（P1）")
async def auto_schedule():
    """用约束求解器基于现有数据自动生成完整排课方案"""
    if not _db.loaded:
        raise HTTPException(status_code=400, detail="请先加载实验安排表（/load-default）")

    from app.engine.auto_scheduler import AutoScheduler
    scheduler = AutoScheduler(_db, student=_student)
    result = scheduler.solve(max_sections=12)

    # 定位说明：自动排课是"辅助初稿生成"，非替代学校已排定的完整安排表
    real_entries = len(_db.entries)
    note = (
        f"📌 定位说明：自动排课为辅助初稿生成（本次简化演示 12 个教学任务），\n"
        f"    学校已排定的完整实验安排表共 {real_entries} 条（含多学院轮转、教师/教室/设备约束），"
        f"可在「我的课程」中查看使用。"
    )
    result["summary_text"] = note + "\n\n" + scheduler.summary(result)

    return {
        "success": result.get("success", False),
        "message": result.get("summary_text", result.get("error", "排课失败")),
        "data": {
            "total_sections": result.get("total_sections", 0),
            "solved": result.get("solved", 0),
            "conflicts": result.get("conflicts", []),
            "schedule": result.get("schedule", []),
            "real_entries": real_entries,
        },
    }


@router.get("/teachers", summary="教师列表（F1 身份选择）")
async def get_teachers():
    """返回全部教师列表（含角色/职称），供身份选择页展示（F1）"""
    if not _db.loaded:
        raise HTTPException(status_code=400, detail="请先加载实验安排表（/load-default）")

    teachers = _db.get_all_teachers()
    roles = _db.get_teacher_roles()  # 从教师联系表提取角色备注
    return {
        "success": True,
        "teachers": [
            {
                "name": name,
                "title": roles.get(name, "实验教师"),
            }
            for name in teachers
        ],
        "total": len(teachers),
    }


@router.get("/teachers/{teacher_name}/courses", summary="教师课程列表（F2）")
async def get_teacher_courses(teacher_name: str):
    """按教师提取课程卡片，标注可调状态（F2）"""
    if not _db.loaded:
        raise HTTPException(status_code=400, detail="请先加载实验安排表（/load-default）")

    courses = _db.get_teacher_courses(teacher_name)
    if not courses:
        raise HTTPException(status_code=404, detail=f"未找到教师「{teacher_name}」的课程")

    return {
        "success": True,
        "teacher": teacher_name,
        "courses": courses,
        "total": len(courses),
    }


# ==================== 调课申请单（F6 审批流，SQLite 持久化） ====================

class RescheduleRequestCreate(BaseModel):
    """教师提交调课申请"""
    teacher: str
    course_name: str
    class_name: str = ""
    original_time: str = ""
    target_week: int
    reason: str = ""


class RescheduleRequestApprove(BaseModel):
    """管理员审批"""
    approve: bool  # True=同意, False=驳回
    comment: str = ""


# SQLite 存储（重启不丢数据）
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "requests.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)


def _get_db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            course_name TEXT NOT NULL,
            class_name TEXT DEFAULT '',
            original_time TEXT DEFAULT '',
            target_week INTEGER NOT NULL,
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            admin_comment TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


_init_db()


@router.post("/requests", summary="教师提交调课申请（F6）")
async def create_request(req: RescheduleRequestCreate):
    """教师提交调课申请，状态初始为 pending（SQLite 持久化）"""
    conn = _get_db()
    # 保留上限：超过 200 条时清理最早的已完成记录，避免演示数据膨胀
    try:
        count_row = conn.execute("SELECT COUNT(*) as c FROM requests").fetchone()
        if count_row["c"] >= 200:
            conn.execute(
                "DELETE FROM requests WHERE status != 'pending' "
                "AND id NOT IN (SELECT id FROM requests ORDER BY id DESC LIMIT 100)"
            )
            conn.commit()
    except Exception:
        pass  # 清理失败不影响主流程

    cur = conn.execute(
        "INSERT INTO requests (teacher, course_name, class_name, original_time, target_week, reason, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'pending', '2026-2027-1')",
        (req.teacher, req.course_name, req.class_name, req.original_time, req.target_week, req.reason),
    )
    conn.commit()
    record = dict(cur.execute("SELECT * FROM requests WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.close()
    return {"success": True, "message": "✅ 调课申请已提交，等待管理员审批", "request": record}


@router.delete("/requests", summary="清空调课申请（调试/演示用）")
async def clear_requests():
    """清空全部调课申请（调试/演示重置用）"""
    conn = _get_db()
    conn.execute("DELETE FROM requests")
    conn.commit()
    conn.close()
    return {"success": True, "message": "✅ 已清空全部调课申请"}


@router.get("/requests", summary="调课申请列表（F6）")
async def list_requests(status: str = ""):
    """查看调课申请列表，可按状态过滤（pending/approved/rejected）"""
    conn = _get_db()
    if status:
        rows = conn.execute("SELECT * FROM requests WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return {"success": True, "requests": items, "total": len(items)}


@router.post("/requests/{request_id}/approve", summary="管理员审批（F6）")
async def approve_request(request_id: int, req: RescheduleRequestApprove):
    """管理员审批调课申请：同意 → approved；驳回 → rejected（填写原因）"""
    conn = _get_db()
    row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"未找到申请单 #{request_id}")

    if row["status"] != "pending":
        conn.close()
        raise HTTPException(status_code=400, detail=f"该申请已审批（状态：{row['status']}），不能重复操作")

    if req.approve:
        status = "approved"
        comment = req.comment or "同意调课"
        message = "✅ 已同意调课申请，请在教务系统中完成修改"
    else:
        status = "rejected"
        comment = req.comment or "未说明原因"
        message = f"❌ 已驳回调课申请（原因：{comment}）"

    conn.execute("UPDATE requests SET status = ?, admin_comment = ? WHERE id = ?", (status, comment, request_id))
    conn.commit()
    record = dict(conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone())
    conn.close()
    return {"success": True, "message": message, "request": record}
