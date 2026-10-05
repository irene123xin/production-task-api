from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, DbSession
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskPage, TaskResponse, TaskUpdate
from app.services.tasks import TaskService

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession, current_user: CurrentUser) -> Task:
    return TaskService(db).create(current_user.id, payload)


@router.get("", response_model=TaskPage)
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100, pattern=r".*\S.*")] = None,
    sort_by: Literal["created_at", "updated_at", "due_date", "title"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> TaskPage:
    return TaskService(db).list(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        task_status=task_status,
        priority=priority,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Task:
    return TaskService(db).get_owned(task_id, current_user.id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession, current_user: CurrentUser) -> Task:
    return TaskService(db).update(task_id, current_user.id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    TaskService(db).delete(task_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
