from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def profile(current_user: CurrentUser) -> User:
    return current_user
