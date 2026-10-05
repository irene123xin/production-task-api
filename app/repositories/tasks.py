from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_owned(self, task_id: int, owner_id: int) -> Task | None:
        return self.db.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner_id))

    def list_owned(
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
    ) -> tuple[list[Task], int]:
        query: Select[tuple[Task]] = select(Task).where(Task.owner_id == owner_id)
        if task_status is not None:
            query = query.where(Task.status == task_status)
        if priority is not None:
            query = query.where(Task.priority == priority)
        if search:
            pattern = f"%{_escape_like(search.strip())}%"
            query = query.where(
                or_(Task.title.ilike(pattern, escape="\\"), Task.description.ilike(pattern, escape="\\"))
            )

        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = self.db.scalar(count_query) or 0
        sort_column = getattr(Task, sort_by)
        ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        if sort_by == "due_date":
            ordering = ordering.nulls_last()
        id_ordering = Task.id.asc() if sort_order == "asc" else Task.id.desc()
        query = query.order_by(ordering, id_ordering)
        items = list(self.db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all())
        return items, total

    def save(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.commit()
