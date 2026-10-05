import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.task import Task, TaskPriority
from app.models.user import User


def seed() -> None:
    password = os.getenv("SEED_DEMO_PASSWORD")
    if password is None or len(password) < 8:
        raise RuntimeError("Set SEED_DEMO_PASSWORD to at least 8 characters before running the seed script")
    with SessionLocal() as db:
        email = "demo@example.com"
        if db.scalar(select(User).where(User.email == email)):
            print("Demo user already exists")
            return
        user = User(email=email, full_name="Demo User", hashed_password=hash_password(password))
        user.tasks = [
            Task(title="Review API documentation", priority=TaskPriority.HIGH),
            Task(title="Plan next sprint", priority=TaskPriority.MEDIUM),
        ]
        db.add(user)
        db.commit()
        print("Created demo@example.com with two tasks")


if __name__ == "__main__":
    seed()
