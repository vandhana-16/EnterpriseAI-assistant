from fastapi import APIRouter
from app.services.rag_service import get_rag_service
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@router.get("/stats")
async def stats():
    rag = get_rag_service()
    return {
        "app": settings.APP_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        **rag.get_stats(),
    }
