from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Task, User, UserRole
from app.notification_history import notify_user_and_record
from app.schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

_ASSIGNABLE_ROLES = {UserRole.WORKER, UserRole.MANAGER, UserRole.ACCOUNTANT}


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        assigned_to_id=task.assigned_to_id,
        assigned_to_name=task.assignee.name if task.assignee else None,
        assigned_by_id=task.assigned_by_id,
        assigned_by_name=task.assigner.name if task.assigner else None,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _require_admin_or_manager(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can perform this action",
        )


def _get_assignable_user(db: Session, user_id: int) -> User:
    assignee = db.query(User).filter(User.id == user_id).first()
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignee not found",
        )
    if assignee.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasks can only be assigned to workers, managers, or accountants",
        )
    return assignee


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin_or_manager(current_user)
    assignee = _get_assignable_user(db, task_data.assigned_to_id)

    new_task = Task(
        title=task_data.title.strip(),
        description=task_data.description.strip() if task_data.description else None,
        assigned_to_id=assignee.id,
        assigned_by_id=current_user.id,
        priority=task_data.priority,
        due_date=task_data.due_date,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    task = (
        db.query(Task)
        .options(joinedload(Task.assignee), joinedload(Task.assigner))
        .filter(Task.id == new_task.id)
        .first()
    )

    due_str = f" Due: {task.due_date}." if task.due_date else ""
    notify_user_and_record(
        db,
        assignee,
        title="New task assigned",
        body=f"{task.title}.{due_str}",
        notification_type="task_assigned",
        sent_by_user_id=current_user.id,
        data={"type": "task_assigned", "task_id": str(task.id)},
    )

    return _task_to_response(task)


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    assigned_to_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).options(joinedload(Task.assignee), joinedload(Task.assigner))

    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        if assigned_to_id is not None:
            query = query.filter(Task.assigned_to_id == assigned_to_id)
    else:
        query = query.filter(Task.assigned_to_id == current_user.id)

    if status_filter:
        query = query.filter(Task.status == status_filter)

    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return [_task_to_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .options(joinedload(Task.assignee), joinedload(Task.assigner))
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        if task.assigned_to_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this task",
            )

    return _task_to_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .options(joinedload(Task.assignee), joinedload(Task.assigner))
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    is_admin_or_manager = current_user.role in (UserRole.ADMIN, UserRole.MANAGER)
    is_assignee = task.assigned_to_id == current_user.id

    if not is_admin_or_manager and not is_assignee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task",
        )

    if not is_admin_or_manager:
        if task_data.status is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update task status",
            )
        task.status = task_data.status
    else:
        if task_data.title is not None:
            task.title = task_data.title.strip()
        if task_data.description is not None:
            task.description = task_data.description.strip() or None
        if task_data.status is not None:
            task.status = task_data.status
        if task_data.priority is not None:
            task.priority = task_data.priority
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        if task_data.assigned_to_id is not None:
            assignee = _get_assignable_user(db, task_data.assigned_to_id)
            if assignee.id != task.assigned_to_id:
                task.assigned_to_id = assignee.id
                notify_user_and_record(
                    db,
                    assignee,
                    title="Task reassigned to you",
                    body=task.title,
                    notification_type="task_assigned",
                    sent_by_user_id=current_user.id,
                    data={"type": "task_assigned", "task_id": str(task.id)},
                )

    db.commit()
    db.refresh(task)
    return _task_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin_or_manager(current_user)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    db.delete(task)
    db.commit()
    return None
