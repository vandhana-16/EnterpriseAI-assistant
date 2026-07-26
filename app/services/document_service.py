import os
import uuid
import logging
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Document
from app.core.config import settings
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


async def upload_document(file: UploadFile, user_id: int, db: AsyncSession) -> Document:
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file bytes
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save to disk with UUID name (avoids collisions)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        filename=unique_name,
        original_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        uploaded_by=user_id,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Ingest into ChromaDB (background-style — runs synchronously here)
    try:
        rag = get_rag_service()
        num_chunks = await rag.ingest_pdf(file_path, doc.id)
        doc.num_chunks = num_chunks
        doc.status = "ready"
    except Exception as e:
        logger.error(f"Ingestion failed for doc {doc.id}: {e}")
        doc.status = "failed"

    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return result.scalars().all()


async def delete_document(doc_id: int, user_id: int, user_role: str, db: AsyncSession):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Only admin or uploader can delete
    if user_role != "admin" and doc.uploaded_by != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # Remove from ChromaDB
    try:
        rag = get_rag_service()
        await rag.delete_document(doc_id)
    except Exception as e:
        logger.warning(f"Could not remove from vectorstore: {e}")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.commit()
    return {"message": f"Document '{doc.original_name}' deleted successfully"}
