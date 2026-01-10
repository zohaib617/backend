"""
User model for TodoApp Backend API.

This module defines the User entity for authentication.
Note: Better Auth typically manages users, but we define
the model here for integration with our JWT system.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.models.task import Task


class User(SQLModel, table=True):
    """
    User entity for authentication.

    This model represents the user table for our JWT-based authentication.
    In a real implementation with Better Auth, user management would be
    handled by Better Auth's database, but we're including password fields
    for our custom authentication endpoints.

    Attributes:
        id: Unique identifier (UUID)
        email: User's email address (unique)
        name: User's display name
        email_verified: Whether email has been verified
        image: Optional profile image URL
        hashed_password: Hashed password for authentication
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        tasks: Relationship to user's tasks
    """

    __tablename__ = "user"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="Unique identifier for the user"
    )

    email: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False,
        description="User's email address"
    )

    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's display name"
    )

    email_verified: bool = Field(
        default=False,
        nullable=False,
        description="Whether the user's email has been verified"
    )

    image: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to user's profile image"
    )

    hashed_password: str = Field(
        max_length=255,
        nullable=False,
        description="Hashed password for authentication"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Timestamp when user was created"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Timestamp when user was last updated"
    )

    # Relationships
    tasks: list["Task"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
