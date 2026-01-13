"""
Task API endpoints for TodoApp Backend (Optimized Pro Version).
Fixes: 307 Redirects, Memory Leaks in Counting, and Code Duplication.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func  # 'func' is critical for efficient counting
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.middleware.auth import get_current_user_id
from src.models import Task
from src.models.task import TaskPriority
from src.schemas import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

# 'redirect_slashes=False' prevent karta hai 307 errors ko agar frontend slash miss karde
router = APIRouter(prefix="/tasks", tags=["Tasks"], redirect_slashes=False)

# --- Helper Functions (To keep code DRY) ---

async def get_task_or_404(task_id: UUID, user_id: UUID, session: AsyncSession) -> Task:
    """Helper to fetch a task and verify ownership in one go."""
    query = select(Task).where(Task.id == task_id, Task.owner_id == user_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    return task

# --- Routes ---

@router.get("", response_model=TaskListResponse) # Use "" to match prefix exactly
async def get_tasks(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    completed: Optional[bool] = None,
    priority: Optional[TaskPriority] = None,
) -> TaskListResponse:
    """
    Get tasks for the current user with optimized SQL counting and filtering.
    """
    # 1. Base query for data
    query = select(Task).where(Task.owner_id == current_user_id)
    
    # 2. Optimized Count query (Does NOT load records into memory)
    count_query = select(func.count()).select_from(Task).where(Task.owner_id == current_user_id)

    # Apply Filters to both queries
    if completed is not None:
        query = query.where(Task.completed == completed)
        count_query = count_query.where(Task.completed == completed)

    if priority is not None:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)

    # 3. Execution: Data + Total Count
    # Pagination aur Sorting
    data_query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())
    
    tasks_result = await session.execute(data_query)
    tasks = tasks_result.scalars().all()
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0 # Direct integer return

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if limit > 0 else 1,
    )

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_create: TaskCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """Create a task with automatic owner assignment."""
    task = Task(
        **task_create.model_dump(),
        owner_id=current_user_id,
    ) #

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
    """Get specific task using helper function."""
    task = await get_task_or_404(task_id, current_user_id, session)
    return TaskResponse.model_validate(task)

@router.put("/{task_id}", response_model=TaskResponse)
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    Handles both PUT and PATCH. 
    Uses 'exclude_unset=True' to only update fields sent by client.
    """
    task = await get_task_or_404(task_id, current_user_id, session)

    update_data = task_update.model_dump(exclude_unset=True) #
    for field, value in update_data.items():
        setattr(task, field, value) #

    await session.commit()
    await session.refresh(task)

    return TaskResponse.model_validate(task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete task with ownership verification."""
    task = await get_task_or_404(task_id, current_user_id, session)
    
    await session.delete(task) #
    await session.commit()