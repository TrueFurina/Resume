"""解析学生课表 PDF，提取课程占用时间段"""

import re
from typing import List, Dict, Set, Tuple, Optional


class StudentCourse:
    """学生的一门课程"""
    def __init__(self, name: str, weekday: str, periods: str, weeks: str,
                 room: str = "", teacher: str = ""):
        self.name = name
        self.weekday = weekday      # 周一~周日
        self.periods = periods      # 节次，如 "1-2节" "5-7节"
        self.weeks = weeks          # 周次，如 "1-15周" "4周" "5-10周"
        self.room = room
        self.teacher = teacher

    def parse_weeks(self) -> Set[int]:
        """解析周次字符串为具体周数集合"""
        weeks = set()
        for part in self.weeks.replace("周", "").split(","):
            part = part.strip()
            if not part:
                continue
            # 处理 "1-15" "4" "2-16(双)" "1-15(单)" 等
            m = re.match(r'^(\d+)(?:-(\d+))?(?:\((\w+)\))?$', part)
            if not m:
                continue
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start
            parity = m.group(3)  # 单/双 or None

            for w in range(start, end + 1):
                if parity == "单" and w % 2 == 0:
                    continue
                if parity == "双" and w % 2 == 1:
                    continue
                weeks.add(w)
        return weeks

    def period_to_time_slot(self) -> Optional[str]:
        """把节次转换为系统时间段标记"""
        m = re.match(r'^(\d+)-(\d+)节$', self.periods.strip())
        if not m:
            return None
        start = int(m.group(1))
        end = int(m.group(2))
        # 映射到实验排课的时间段
        if start <= 2:
            return "上午"  # 上午有课
        if start >= 9:
            return "91011"  # 晚上
        if end <= 4:
            return "34"     # 下午前段
        if start == 5 or start == 6:
            return "567"    # 下午 5-7 节
        if start == 7 or start == 8:
            return "78"     # 下午 7-8 节
        return None

    def __repr__(self):
        return f"{self.name} {self.weekday} {self.periods} {self.weeks}"


class StudentScheduleParser:
    """解析学生课表 PDF"""

    WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.courses: List[StudentCourse] = []

    def parse(self) -> List[StudentCourse]:
        """解析 PDF 提取课程"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(self.pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
        except ImportError:
            from pypdf import PdfReader
            reader = PdfReader(self.pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

        self.courses = self._extract_courses(text)
        return self.courses

    def _extract_courses(self, text: str) -> List[StudentCourse]:
        """从 PDF 文本提取课程信息"""
        courses = []
        # 按星期几分段
        # PDF 结构：时间段行包含 "1-2节" "3-4节" "5-7节" 等
        # 课程块：课程名 (节次)周次/场地/教师

        # 每门课的模式：课程名 + (X-Y节) + 周次 + 场地 + 教师
        pattern = re.compile(
            r'([\u4e00-\u9fff\w]+)'
            r'\s*\((\d+-\d+节)\)\s*'
            r'([\d,\-\(\)单双周]+周)',
        )

        # 找星期几位置，确定课程归属哪一天
        day_positions = []
        for wd in self.WEEKDAYS:
            idx = text.find(wd)
            if idx >= 0:
                day_positions.append((idx, wd))
        day_positions.sort()

        # 把文本按天切分
        segments = []
        for i, (pos, wd) in enumerate(day_positions):
            end = day_positions[i + 1][0] if i + 1 < len(day_positions) else len(text)
            segments.append((wd, text[pos:end]))

        for wd, seg in segments:
            for m in pattern.finditer(seg):
                name = m.group(1).strip()
                periods = m.group(2)
                weeks = m.group(3)

                # 提取场地和教师（课程名后面的完整信息）
                after = seg[m.end():m.end() + 150]
                room_m = re.search(r'场地:([^/]+)', after)
                teacher_m = re.search(r'教师:([^/]+)', after)
                room = room_m.group(1).strip() if room_m else ""
                teacher = teacher_m.group(1).strip() if teacher_m else ""

                # 跳过实践课程汇总行
                if name in ("讲课", "实验", "实训", "实践", "其他课程", "实践课程"):
                    continue
                if "课程学时组成" in name:
                    continue

                course = StudentCourse(
                    name=name,
                    weekday=wd,
                    periods=periods,
                    weeks=weeks,
                    room=room,
                    teacher=teacher,
                )
                courses.append(course)

        return courses

    def get_busy_slots(self, target_week: int) -> Dict[str, Set[str]]:
        """
        获取学生在某周所有被占用的时段
        返回: {"周一": {"567", "34"}, "周二": {...}}
        """
        busy: Dict[str, Set[str]] = {wd: set() for wd in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]}
        for c in self.courses:
            weeks = c.parse_weeks()
            if target_week not in weeks:
                continue
            ts = c.period_to_time_slot()
            if ts and ts != "上午":
                short_wd = c.weekday.replace("星期", "周")
                if short_wd in busy:
                    busy[short_wd].add(ts)
        return busy
