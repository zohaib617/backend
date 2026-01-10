"""
Task schemas for TodoApp Backend API.

This module defines Pydantic schemas for Task entity validation
in API requests and responses.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.models.task import TaskPriority


class TaskBase(BaseModel):
    """Base schema for Task with common fields."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional task description"
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level"
    )
    due_date: Optional[date] = Field(
        None,
        description="Optional due date for the task"
    )
    completed: bool = Field(
        default=False,
        description="Whether the task is completed"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    pass


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.

    All fields are optional to support partial updates.
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Task description"
    )
    priority: Optional[TaskPriority] = Field(
        None,
        description="Task priority level"
    )
    due_date: Optional[date] = Field(
        None,
        description="Due date for the task"
    )
    completed: Optional[bool] = Field(
        None,
        description="Whether the task is completed"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate title is not empty or whitespace only."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Title cannot be empty or whitespace only")
            return v.strip()
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TaskResponse(TaskBase):
    """Schema for task responses."""

    id: UUID = Field(..., description="Unique identifier for the task")
    owner_id: UUID = Field(..., description="ID of the user who owns this task")
    created_at: datetime = Field(..., description="Timestamp when task was created")
    updated_at: datetime = Field(..., description="Timestamp when task was last updated")

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for paginated task list responses."""

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        from_attributes = True
