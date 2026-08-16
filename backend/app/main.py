"""物理实验调课辅助系统 - 后端入口（最小闭环）"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import reschedule

app = FastAPI(
    title="物理实验调课辅助系统",
    description="上传实验安排表 → AI筛选空闲时段 → 教师选择 → 管理员审批",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 只注册调课相关的路由
app.include_router(reschedule.router, prefix="/api/reschedule", tags=["调课管理"])


@app.get("/")
def root():
    return {
        "message": "物理实验调课辅助系统 API",
        "version": "0.1.0",
        "usage": "POST /api/reschedule/upload 上传实验安排表 → POST /api/reschedule/chat 调课咨询",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
