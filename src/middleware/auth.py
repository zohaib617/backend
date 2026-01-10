"""
JWT Authentication middleware and utilities for TodoApp Backend API.

This module provides JWT token creation, verification, and authentication
dependencies for FastAPI routes.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session
from src.models import User

# HTTP Bearer token scheme
security = HTTPBearer()


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: The user's unique identifier
        expires_delta: Optional custom expiration time. If not provided,
                      uses JWT_ACCESS_TOKEN_EXPIRE_MINUTES from settings

    Returns:
        str: Encoded JWT token

    Example:
        ```python
        token = create_access_token(user_id=user.id)
        # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        ```
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": str(user_id),  # Subject: user ID
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> UUID:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        UUID: The user ID extracted from the token

    Raises:
        HTTPException: If token is invalid, expired, or malformed

    Example:
        ```python
        try:
            user_id = verify_token(token)
        except HTTPException:
            # Handle invalid token
            pass
        ```
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        user_id_str: Optional[str] = payload.get("sub")

        if user_id_str is None:
            raise credentials_exception

        # Convert string to UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise credentials_exception

        return user_id

    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    This dependency extracts the JWT token from the Authorization header,
    verifies it, and retrieves the corresponding user from the database.

    Args:
        credentials: HTTP Bearer credentials from the request header
        session: Database session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: If token is invalid or user not found

    Example:
        ```python
        @app.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id, "email": current_user.email}
        ```
    """
    token = credentials.credentials
    user_id = verify_token(token)

    # Query user from database
    from sqlalchemy import select

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    FastAPI dependency to get the current user's ID without database lookup.

    This is a lightweight alternative to get_current_user when you only
    need the user ID and don't need the full user object.

    Args:
        credentials: HTTP Bearer credentials from the request header

    Returns:
        UUID: The authenticated user's ID

    Raises:
        HTTPException: If token is invalid

    Example:
        ```python
        @app.get("/tasks")
        async def get_tasks(user_id: UUID = Depends(get_current_user_id)):
            # Use user_id to filter tasks
            pass
        ```
    """
    token = credentials.credentials
    return verify_token(token)


def verify_user_ownership(resource_owner_id: UUID, current_user_id: UUID) -> None:
    """
    Verify that the current user owns the resource.

    This function enforces user isolation by ensuring that users can only
    access their own resources.

    Args:
        resource_owner_id: The owner ID of the resource being accessed
        current_user_id: The ID of the currently authenticated user

    Raises:
        HTTPException: If the user doesn't own the resource (403 Forbidden)

    Example:
        ```python
        @app.get("/tasks/{task_id}")
        async def get_task(
            task_id: UUID,
            current_user_id: UUID = Depends(get_current_user_id),
            session: AsyncSession = Depends(get_session)
        ):
            task = await get_task_by_id(task_id, session)
            verify_user_ownership(task.owner_id, current_user_id)
            return task
        ```
    """
    if resource_owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
