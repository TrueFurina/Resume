"""认证 API"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.user import User, UserRole
from app.config import settings
from jose import JWTError, jwt
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# ---- Pydantic Schemas ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: UserRole = UserRole.STUDENT
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    email: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ---- 工具函数 ----
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---- API 端点 ----
@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )


@router.post("/register", response_model=UserResponse)
def register(req: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        hashed_password=pwd_context.hash(req.password),
        display_name=req.display_name,
        role=req.role,
        email=req.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
