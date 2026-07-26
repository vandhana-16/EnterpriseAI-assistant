from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.schemas import UserOut
from app.services.auth_service import list_all_users
from app.core.security import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    List every registered user (id, email, name, role, status).

    Role-based access control: only accounts with role == "admin" may call
    this endpoint. Everyone else gets a 403, even with a valid token.
    The very first account ever registered on a fresh install is
    automatically made admin — see auth_service.register_user().
    """
    return await list_all_users(db)
