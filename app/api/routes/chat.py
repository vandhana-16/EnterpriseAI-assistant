from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.schemas import AskQuestion, AskResponse
from app.services.chat_service import ask_question, get_chat_history
from app.core.security import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat / Q&A"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskQuestion,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Ask a question in natural language.
    The RAG pipeline retrieves relevant document chunks and generates an answer.
    """
    result = await ask_question(body.question, current_user["user_id"], db)
    return result


@router.get("/history", response_model=list)
async def history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get your last N questions and answers."""
    return await get_chat_history(current_user["user_id"], db, limit)
