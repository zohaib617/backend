"""
Task model for TodoApp Backend API.

This module defines the Task entity with all required fields,
indexes, and relationships as specified in the data model.
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.models.user import User


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(SQLModel, table=True):
    """
    Task entity for todo items.

    Each task belongs to a single user (owner) and contains all necessary
    fields for task management including title, description, priority,
    due date, and completion status.

    Attributes:
        id: Unique identifier (UUID)
        owner_id: Foreign key to User (indexed for performance)
        title: Task title (max 200 characters)
        description: Optional task description (max 2000 characters)
        priority: Task priority (low, medium, high)
        due_date: Optional due date
        completed: Whether task is completed
        created_at: Timestamp when task was created
        updated_at: Timestamp when task was last updated
        owner: Relationship to User who owns this task
    """

    __tablename__ = "task"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="Unique identifier for the task"
    )

    owner_id: UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True,  # Critical index for user isolation queries
        description="Foreign key to the user who owns this task"
    )

    title: str = Field(
        max_length=200,
        nullable=False,
        description="Task title"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional task description"
    )

    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,  # Index for filtering by priority
        description="Task priority level"
    )

    due_date: Optional[date] = Field(
        default=None,
        description="Optional due date for the task"
    )

    completed: bool = Field(
        default=False,
        nullable=False,
        index=True,  # Index for filtering by completion status
        description="Whether the task is completed"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Timestamp when task was created"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Timestamp when task was last updated"
    )

    # Relationships
    owner: "User" = Relationship(back_populates="tasks")
