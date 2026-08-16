"""AI Agent - 基于 LLM 的智能排课助手（接入讯飞星火）"""

import json
from typing import Optional, List, Dict

import httpx
from pydantic import BaseModel


class AgentRequest(BaseModel):
    """用户请求"""
    prompt: str
    context: Optional[dict] = None


class AgentResponse(BaseModel):
    """Agent 响应"""
    reply: str
    action: Optional[str] = None
    data: Optional[dict] = None


class SchedulingAgent:
    """
    排课智能体 - 处理自然语言排课需求

    功能：
    1. 自然语言 → 排课参数
    2. 排课冲突智能检测
    3. 课程推荐（基于学生历史选课）
    4. 课表查询与答疑
    """

    # 讯飞星火 API 配置
    SPARK_API_URL = "https://spark-api-open.xf-yun.com/x2/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "lite",
    ):
        self.api_key = api_key
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.messages: List[Dict[str, str]] = []

    def _build_system_prompt(self) -> str:
        return """你是一个物理学科智能排课系统的 AI 助手。你可以帮助：

1. **排课咨询** - 回答课程安排、教师排课、教室使用等问题
2. **选课推荐** - 根据学生情况推荐合适的课程
3. **冲突检测** - 分析排课方案中的时间/资源冲突
4. **排课优化** - 提供排课调整建议

请基于用户的问题和系统数据给出专业、清晰的回答。
如果用户要求执行具体操作（如排课、调课），请确认后再执行。
回答请使用中文。
"""

    def _build_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_payload(self, user_message: str) -> dict:
        messages = [{"role": "system", "content": self.system_prompt}]
        for m in self.messages[-10:]:  # 保留最近 10 轮对话
            messages.append(m)
        messages.append({"role": "user", "content": user_message})

        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }

    def _call_llm(self, user_message: str) -> str:
        """调用讯飞星火 API"""
        if not self.api_key:
            return "（AI Agent 未配置 API Key，请设置 LLM_API_KEY）"

        payload = self._build_payload(user_message)

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    self.SPARK_API_URL,
                    headers=self._build_headers(),
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    # 保存对话历史
                    self.messages.append({"role": "user", "content": user_message})
                    self.messages.append({"role": "assistant", "content": reply})
                    return reply
                else:
                    return f"（API 调用失败：HTTP {resp.status_code} - {resp.text[:200]}）"
        except Exception as e:
            return f"（API 调用异常：{str(e)}）"

    async def chat(self, request: AgentRequest) -> AgentResponse:
        """处理用户消息"""
        context_info = ""
        if request.context:
            context_info = "\n\n系统当前数据概要：\n"
            if "courses_count" in request.context:
                context_info += f"- 课程总数：{request.context['courses_count']}\n"
            if "teachers_count" in request.context:
                context_info += f"- 教师总数：{request.context['teachers_count']}\n"
            if "classrooms_count" in request.context:
                context_info += f"- 教室总数：{request.context['classrooms_count']}\n"
            if "slots_count" in request.context:
                context_info += f"- 已排课时间段：{request.context['slots_count']}\n"

        full_prompt = request.prompt + context_info
        reply = self._call_llm(full_prompt)

        return AgentResponse(reply=reply, action="chat")

    def detect_conflict(self, schedule_data: dict) -> list:
        """检测排课冲突"""
        conflicts = []
        slots = schedule_data.get("slots", [])
        for i, s1 in enumerate(slots):
            for s2 in slots[i + 1:]:
                if s1.get("weekday") == s2.get("weekday") and s1.get("time_slot") == s2.get("time_slot"):
                    if s1.get("teacher_id") and s1["teacher_id"] == s2.get("teacher_id"):
                        conflicts.append({
                            "type": "teacher_time_conflict",
                            "detail": f"教师 ID {s1['teacher_id']} 在 {s1['weekday']} {s1['time_slot']} 有冲突",
                        })
                    if s1.get("classroom_id") and s1["classroom_id"] == s2.get("classroom_id"):
                        conflicts.append({
                            "type": "classroom_conflict",
                            "detail": f"教室 ID {s1['classroom_id']} 在 {s1['weekday']} {s1['time_slot']} 被重复使用",
                        })
        return conflicts
