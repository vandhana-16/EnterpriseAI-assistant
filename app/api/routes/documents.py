from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.schemas import DocumentOut
from app.services.document_service import upload_document, list_documents, delete_document
from app.core.security import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a PDF document. It will be chunked, embedded, and stored in ChromaDB.
    Any employee can upload documents.
    """
    doc = await upload_document(file, current_user["user_id"], db)
    return doc


@router.get("/", response_model=list[DocumentOut])
async def get_documents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all uploaded documents."""
    return await list_documents(db)


@router.delete("/{doc_id}")
async def remove_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a document (admin or uploader only)."""
    return await delete_document(
        doc_id,
        current_user["user_id"],
        current_user["role"],
        db,
    )
