from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate, TaskPage, TaskUpdate


class TaskService:
    def __init__(self, db: Session) -> None:
        self.tasks = TaskRepository(db)

    def create(self, owner_id: int, payload: TaskCreate) -> Task:
        return self.tasks.create(Task(owner_id=owner_id, **payload.model_dump()))

    def get_owned(self, task_id: int, owner_id: int) -> Task:
        task = self.tasks.get_owned(task_id, owner_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def list(
        self,
        *,
        owner_id: int,
        page: int,
        page_size: int,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> TaskPage:
        items, total = self.tasks.list_owned(
            owner_id=owner_id,
            page=page,
            page_size=page_size,
            task_status=task_status,
            priority=priority,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return TaskPage(items=items, page=page, page_size=page_size, total=total, pages=ceil(total / page_size))

    def update(self, task_id: int, owner_id: int, payload: TaskUpdate) -> Task:
        task = self.get_owned(task_id, owner_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        return self.tasks.save(task)

    def delete(self, task_id: int, owner_id: int) -> None:
        self.tasks.delete(self.get_owned(task_id, owner_id))
