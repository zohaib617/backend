"""
Task API endpoints for TodoApp Backend.

This module implements the REST API endpoints for task management
with JWT authentication and user isolation.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.middleware.auth import get_current_user_id, verify_user_ownership
from src.models import Task, User
from src.models.task import TaskPriority
from src.schemas import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=TaskListResponse)
async def get_tasks(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    completed: bool = None,
    priority: TaskPriority = None,
) -> TaskListResponse:
    """
    Get tasks for the current user with optional filtering.

    Args:
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        completed: Filter by completion status
        priority: Filter by priority level

    Returns:
        TaskListResponse: List of tasks with pagination info

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Build query with user isolation
    query = select(Task).where(Task.owner_id == current_user_id)

    # Apply filters
    if completed is not None:
        query = query.where(Task.completed == completed)

    if priority is not None:
        query = query.where(Task.priority == priority)

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())

    result = await session.execute(query)
    tasks = result.scalars().all()

    # Get total count for pagination
    count_query = select(Task).where(Task.owner_id == current_user_id)
    if completed is not None:
        count_query = count_query.where(Task.completed == completed)
    if priority is not None:
        count_query = count_query.where(Task.priority == priority)

    count_result = await session.execute(count_query)
    total = len(count_result.scalars().all())

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if limit > 0 else 1,
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_create: TaskCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Create a new task for the current user.

    Args:
        task_create: Task creation data
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session

    Returns:
        TaskResponse: Created task data

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Create task with owner_id set to current user
    task = Task(
        **task_create.model_dump(),
        owner_id=current_user_id,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Get a specific task by ID.

    Args:
        task_id: ID of the task to retrieve
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session

    Returns:
        TaskResponse: Task data

    Raises:
        HTTPException: 401 if not authenticated, 403 if not owned by user, 404 if not found
    """
    # Query task by ID and owner
    query = select(Task).where(Task.id == task_id, Task.owner_id == current_user_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have permission to access it",
        )

    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Update a task completely.

    Args:
        task_id: ID of the task to update
        task_update: Task update data
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session

    Returns:
        TaskResponse: Updated task data

    Raises:
        HTTPException: 401 if not authenticated, 403 if not owned by user, 404 if not found
    """
    # Query task by ID and owner
    query = select(Task).where(Task.id == task_id, Task.owner_id == current_user_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have permission to access it",
        )

    # Update task fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)

    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def partial_update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Partially update a task.

    Args:
        task_id: ID of the task to update
        task_update: Task update data (only specified fields will be updated)
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session

    Returns:
        TaskResponse: Updated task data

    Raises:
        HTTPException: 401 if not authenticated, 403 if not owned by user, 404 if not found
    """
    # Query task by ID and owner
    query = select(Task).where(Task.id == task_id, Task.owner_id == current_user_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have permission to access it",
        )

    # Update only specified fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)

    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a task.

    Args:
        task_id: ID of the task to delete
        current_user_id: ID of the authenticated user (from JWT)
        session: Database session

    Raises:
        HTTPException: 401 if not authenticated, 403 if not owned by user, 404 if not found
    """
    # Query task by ID and owner
    query = select(Task).where(Task.id == task_id, Task.owner_id == current_user_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have permission to access it",
        )

    await session.delete(task)
    await session.commit()