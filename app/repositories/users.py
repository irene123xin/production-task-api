from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()
        return self.db.scalar(select(User).where(func.lower(User.email) == normalized_email))

    def create(self, *, email: str, full_name: str, hashed_password: str) -> User:
        user = User(email=email.strip().lower(), full_name=full_name, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
