"""解析学生课表 PDF，提取课程（利用文本坐标定位星期归属）

PDF 课表是表格格式：行=节次，列=星期几。
纯文本提取会丢失列归属（全部挤在一起），因此使用 PyMuPDF 的
文本坐标（bbox）来判断每个课程块属于哪一列（星期几）。

解析结果格式：[(课程名, 星期, 节次, 周次), ...]
"""

import re
from typing import List, Tuple, Dict, Optional


class PdfScheduleParser:
    """PDF 学生课表解析器"""

    WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    # 列 x0 区间（闽江学院教务课表版式：列宽约135pt，首列x≈80）
    COLUMN_RANGES = [
        ("周一", (0, 150)),
        ("周二", (150, 290)),
        ("周三", (290, 420)),
        ("周四", (420, 560)),
        ("周五", (560, 690)),
        ("周六", (690, 830)),
        ("周日", (830, 1000)),
    ]

    def __init__(self):
        self.weekday_columns: Dict[str, Tuple[float, float]] = {}  # 星期 → (x_min, x_max)
        self.courses: List[Tuple[str, str, str, str]] = []

    def parse(self, pdf_path: str) -> List[Tuple[str, str, str, str]]:
        """解析 PDF 课表"""
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        # 合并所有页的文本块
        all_blocks = []
        for page in doc:
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, block_no, block_type = b
                if block_type == 0:  # 文本块
                    all_blocks.append((x0, y0, x1, y1, text.strip()))

        # 2. 提取课程块并按 x0 坐标归类到星期列
        self.courses = self._extract_courses(all_blocks)
        return self.courses

    def _column_for_x(self, x0: float) -> Optional[str]:
        """根据块的左边界 x0 判断属于哪个星期列"""
        for wd, (x_min, x_max) in self.COLUMN_RANGES:
            if x_min <= x0 < x_max:
                return wd
        return None

    def _extract_courses(self, blocks: List[Tuple]) -> List[Tuple[str, str, str, str]]:
        """从文本块中提取课程信息

        PDF 课表中，课程名块（如 "1|高等数学A2"）和节次信息块
        （如 "(1-2节)1-15周/校区:.../教师:..."）是分离的两个块，
        需要分别匹配后按 x 列区间 + y 距离配对。
        """
        # 1. 匹配节次信息块：提取 (节次, 周次, x0, y0)
        period_pattern = re.compile(r'\((\d+-\d+节)\)\s*([\d,、\-\(\)单双周]+周)')
        period_blocks = []  # (period, weeks, x0, y0)
        for x0, y0, x1, y1, text in blocks:
            m = period_pattern.search(text)
            if m:
                period_blocks.append((m.group(1), m.group(2), x0, y0))

        # 2. 匹配课程名块：不含节次/校区等标识的纯课程名
        name_blocks = []  # (name, x0, y0)
        skip_keywords = ["节)", "校区", "教师", "学时", "考核", "教学班", "场地",
                         "星期", "课表", "学号", "实践课程", "其他课程", "音乐鉴赏",
                         "上课时间", "选课备注", "实训"]
        for x0, y0, x1, y1, text in blocks:
            if not text or len(text) > 40:
                continue
            if any(k in text for k in skip_keywords):
                continue
            if "时间段" in text or "上午" in text or "下午" in text or "晚上" in text:
                continue
            # 去除行号前缀 "1|" 或 "1\n"
            name = re.sub(r'^\d+[\|\n]', '', text.strip())
            name = name.strip().replace("\n", "")
            if not (2 <= len(name) <= 20):
                continue
            # 排除纯数字、表头、含英文字母缩写过长等
            if re.match(r'^\d+$', name):
                continue
            if "2024" in name or "2025" in name:
                continue
            name_blocks.append((name, x0, y0))

        # 3. 配对：对每个节次块，找同列(x0区间)且y最近的课程名块
        courses = []
        used_names = set()
        for period, weeks, p_x0, p_y0 in period_blocks:
            weekday = self._column_for_x(p_x0)
            if not weekday:
                continue

            best_name = None
            best_dist = float("inf")
            for name, n_x0, n_y0 in name_blocks:
                n_weekday = self._column_for_x(n_x0)
                if n_weekday != weekday:
                    continue
                if name in used_names:
                    continue
                dist = abs(n_y0 - p_y0)
                if dist < best_dist:
                    best_dist = dist
                    best_name = name

            if best_name and best_dist < 200:  # 合理y距离
                courses.append((best_name, weekday, period, weeks))
                used_names.add(best_name)

        # 4. 合并：同一课程名+节次的多条记录（如"大学物理实验C (5-7节) 4周/5周/6周..."，
        #    被拆成多列块）合并为一个，周次取并集
        merged: Dict[Tuple[str, str], Dict] = {}
        for name, weekday, period, weeks in courses:
            key = (name, period)
            if key not in merged:
                merged[key] = {"name": name, "weekday": weekday, "period": period, "weeks": set()}
            # 解析周次表达式合并
            merged[key]["weeks"].add(weeks)

        result = []
        for key, info in merged.items():
            name, period = key
            weeks_set = info["weeks"]
            # 简单合并：多个周次表达式取范围并集（如有多个，拼接显示）
            weeks_str = self._merge_week_exprs(weeks_set)
            result.append((name, info["weekday"], period, weeks_str))

        return result

    def _merge_week_exprs(self, exprs: set) -> str:
        """合并多个周次表达式为范围"""
        weeks = set()
        for expr in exprs:
            weeks.update(self._expand_weeks(expr))
        if not weeks:
            return "1-16周"
        # 转范围表示
        return self._compress_weeks(weeks)

    def _expand_weeks(self, expr: str) -> set:
        """展开 '4周' '5-10周' '1-6周,8-10周' 为周数集合"""
        weeks = set()
        for part in expr.replace("周", "").split(","):
            part = part.strip()
            if not part:
                continue
            m = re.match(r'^(\d+)(?:-(\d+))?(?:\((\w+)\))?$', part)
            if not m:
                continue
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start
            parity = m.group(3)
            for w in range(start, end + 1):
                if parity == "单" and w % 2 == 0:
                    continue
                if parity == "双" and w % 2 == 1:
                    continue
                weeks.add(w)
        return weeks

    def _compress_weeks(self, weeks: set) -> str:
        """将周数集合压缩为范围表达式 '4-10周'"""
        if not weeks:
            return ""
        wlist = sorted(weeks)
        ranges = []
        start = prev = wlist[0]
        for w in wlist[1:]:
            if w == prev + 1:
                prev = w
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = prev = w
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        return ",".join(ranges) + "周"
