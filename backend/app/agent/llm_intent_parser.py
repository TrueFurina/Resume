"""律动基元（TokenRhythm）LLM 意图解析器

用 LLM 解析"大白话"调课请求（B1），与规则解析互补：
- 规则解析：处理标准话术（"第六周的课上不了，调到下周"）
- LLM 解析：处理口语化表达（"我下周三有点事，那个课往后挪一周行不行"）

接口：OpenAI 兼容（POST /v1/chat/completions）
凭据：从环境变量 JIYUAN_LVDONG_BASE_URL / JIYUAN_LVDONG_API_KEY 读取
"""

import json
import os
import re
from typing import Optional

import httpx


class LLMIntentParser:
    """律动基元 LLM 意图解析器"""

    BASE_URL = os.environ.get("JIYUAN_LVDONG_BASE_URL", "https://tokenrhythm.studio/v1")
    API_KEY = os.environ.get("JIYUAN_LVDONG_API_KEY", "")
    MODEL = os.environ.get("JIYUAN_LVDONG_MODEL", "deepseek-v4-flash")

    SYSTEM_PROMPT = """你是一个高校物理实验排课系统的意图解析器。
你的任务：把教师用大白话表达的调课请求，解析为结构化的 JSON。

必须提取的信息：
- teacher: 教师姓名（若有，如"吴琳"）
- source_week: 原上课周次（数字，若提到"第六周""这周"等；无则 null）
- target_week: 目标周次（数字，若提到"下周""第5周"等；无则 null）
- target_weekday: 目标星期（如"周一"；无则 null）
- course_hint: 提到的课程线索（如"物理实验""那个课"；无则 null）
- needs_followup: 布尔值，信息是否不完整（缺少教师/源周/目标周任一核心信息时为 true）
- followup_questions: needs_followup 为 true 时的追问问题列表（中文，1-3个）

规则：
- 只提取明确存在的信息，不猜测
- "下周" = 源周 + 1（如果有源周）；没有源周时 target_week=null，needs_followup=true
- 输出必须是合法 JSON，不要输出其他内容"""

    def __init__(self):
        self.configured = bool(self.API_KEY)

    def _build_payload(self, text: str) -> dict:
        return {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"调课请求：{text}"},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }

    def parse(self, text: str) -> dict:
        """调用 LLM 解析意图，返回结构化 JSON"""
        if not self.configured:
            return {"error": "LLM 未配置（缺少 JIYUAN_LVDONG_API_KEY）", "needs_followup": False}

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.API_KEY}",
                    },
                    json=self._build_payload(text),
                )
                if resp.status_code != 200:
                    return {"error": f"LLM 调用失败：HTTP {resp.status_code}", "needs_followup": False}

                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return self._extract_json(content)
        except Exception as e:
            return {"error": f"LLM 调用异常：{str(e)}", "needs_followup": False}

    def _extract_json(self, content: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ``` 块
        m = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试提取第一个 { ... }
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"error": "LLM 输出无法解析为 JSON", "needs_followup": False, "raw": content[:200]}

    def consult(self, question: str, context: str = "", role: str = "general") -> dict:
        """通用咨询方法（选课咨询 / 实验辅导复用，B 批次）

        role: 'course_select' 选课咨询 / 'experiment_tutor' 实验辅导 / 'general' 通用
        context: 系统上下文（课程数据、学生课表摘要等）
        """
        if not self.configured:
            return {"error": "LLM 未配置"}

        role_prompts = {
            "course_select": """你是一个高校物理实验课程的选课咨询助手。

重要背景（必须遵循）：
1. 大学物理实验是公共必修课，理工科学生**强制必选**，不存在"想选选不了"的问题
2. 选课资格主要取决于：培养方案先修要求（如先修/同修大学物理理论课）
3. 回答时要结合系统提供的学生课表数据，给出具体、可操作的结论

回答要求：
- 结论明确（先说"能选/需要满足什么条件"）
- 结合学生课表实际数据判断（如课表是否已有该课程时间）
- 不使用"无法确定""建议咨询"等模糊表述，除非信息确实严重不足
- 用简洁的 markdown 格式（标题+列表）""",
            "experiment_tutor": """你是一个大学物理实验辅导助手。
请帮助学生理解实验原理、数据处理、误差分析、实验报告规范等问题。
回答要求：
- 步骤清晰、公式正确（用 LaTeX 公式）、引用实验规范
- 覆盖仪器误差、系统误差、操作误差、环境误差等维度
- 完整回答不要中途截断，宁可详细
- 不确定的内容不要编造，明确说明""",
            "general": """你是一个物理实验教学智能助手，请专业、清晰地回答用户问题。""",
        }
        system_prompt = role_prompts.get(role, role_prompts["general"])

        user_content = question
        if context:
            user_content = f"{context}\n\n问题：{question}"

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.API_KEY}",
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.5,
                        "max_tokens": 4096,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"LLM 调用失败：HTTP {resp.status_code}"}
                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"reply": content}
        except Exception as e:
            return {"error": f"LLM 调用异常：{str(e)}"}

    def suggest_plans(self, teacher: str, course: str, target_week: int,
                      available_slots: list) -> dict:
        """B3: 用 LLM 从可用时段中生成多个候选方案（呼应"AI 多可能性"评审意见）

        输入：教师、课程、目标周次、可用时段列表（可能很多条）
        输出：2-3 个精选候选方案，每个含时段、教室、推荐理由
        """
        if not self.configured:
            return {"error": "LLM 未配置"}

        # 压缩可用时段：每星期取前2个，避免 token 爆炸
        from collections import defaultdict
        by_day = defaultdict(list)
        for s in available_slots[:40]:
            by_day[s["weekday"]].append(f"{s['time_slot']} {s['room']}")
        slot_summary = "\n".join(
            f"{wd}: {', '.join(items[:2])}" for wd, items in by_day.items()
        )

        prompt = f"""你是高校物理实验排课专家。教师「{teacher}」想把「{course}」调到第{target_week}周。
以下是系统筛选出的可用时段（星期 时段 教室）：

{slot_summary}

请从这些时段中挑选 2-3 个最合理的候选方案，考虑：与原课时间接近、教室类型匹配、教师/学生便利性。
输出 JSON（不要其他内容）：
{{
  "plans": [
    {{
      "weekday": "周一", "time_slot": "567", "room": "A410",
      "reason": "与原周四下午课时段接近，教室类型匹配"
    }}
  ]
}}"""

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.API_KEY}",
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )
                if resp.status_code != 200:
                    return {"error": f"LLM 调用失败：HTTP {resp.status_code}"}

                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                result = self._extract_json(content)
                if "plans" in result:
                    return {"plans": result["plans"]}
                return {"error": "LLM 未返回候选方案", "raw": content[:150]}
        except Exception as e:
            return {"error": f"LLM 调用异常：{str(e)}"}
