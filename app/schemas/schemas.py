from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ─── Auth ─────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Document ─────────────────────────────────────────────────────────────────
class DocumentOut(BaseModel):
    id: int
    original_name: str
    file_size: int
    num_chunks: int
    status: str
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Chat ─────────────────────────────────────────────────────────────────────
class AskQuestion(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    chat_id: int


class ChatHistoryOut(BaseModel):
    id: int
    question: str
    answer: str
    sources: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
