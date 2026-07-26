import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import ChatHistory
from app.services.rag_service import get_rag_service


async def ask_question(question: str, user_id: int, db: AsyncSession) -> dict:
    rag = get_rag_service()
    result = await rag.ask(question)

    # Persist to DB
    chat = ChatHistory(
        user_id=user_id,
        question=question,
        answer=result["answer"],
        sources=json.dumps(result["sources"]),
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return {
        "chat_id": chat.id,
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
    }


async def get_chat_history(user_id: int, db: AsyncSession, limit: int = 20) -> list:
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    )
    chats = result.scalars().all()

    # Parse JSON sources back to list
    history = []
    for chat in chats:
        history.append({
            "id": chat.id,
            "question": chat.question,
            "answer": chat.answer,
            "sources": json.loads(chat.sources or "[]"),
            "created_at": chat.created_at,
        })
    return history
