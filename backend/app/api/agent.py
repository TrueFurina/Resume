"""AI Agent API - 智能排课助手聊天接口"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.classroom import Classroom
from app.models.schedule import ScheduleSlot
from app.agent.llm_agent import SchedulingAgent, AgentRequest as AgentReq
from app.config import settings

router = APIRouter()

# 全局 Agent 实例
_agent: Optional[SchedulingAgent] = None


def get_agent() -> SchedulingAgent:
    global _agent
    if _agent is None:
        _agent = SchedulingAgent(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
        )
    return _agent


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    reply: str
    action: str = "chat"


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """AI 排课助手聊天接口"""
    agent = get_agent()

    # 构建系统上下文
    courses_count = db.query(Course).count()
    teachers_count = db.query(Teacher).count()
    classrooms_count = db.query(Classroom).count()
    slots_count = db.query(ScheduleSlot).count()

    context = {
        "courses_count": courses_count,
        "teachers_count": teachers_count,
        "classrooms_count": classrooms_count,
        "slots_count": slots_count,
    }

    agent_req = AgentReq(prompt=req.prompt, context=context)
    import asyncio
    result = asyncio.run(agent.chat(agent_req))

    return ChatResponse(reply=result.reply, action=result.action or "chat")


@router.get("/status")
def agent_status():
    """检查 Agent 配置状态"""
    agent = get_agent()
    return {
        "configured": bool(agent.api_key),
        "model": agent.model,
        "has_history": len(agent.messages) > 0,
    }
