"""
Authentication API endpoints for TodoApp Backend.

This module implements authentication endpoints for user registration,
login, and session management. Note: Better Auth typically handles
these automatically, but we're implementing custom endpoints for
integration with our JWT system.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.middleware.auth import create_access_token, verify_token
from src.models import User
from src.schemas import TaskResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme for logout endpoint
security = HTTPBearer()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    email: str,
    password: str,
    name: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Register a new user.

    Args:
        request: HTTP request object
        email: User's email address
        password: User's password (will be hashed)
        name: Optional user's display name
        session: Database session

    Returns:
        dict: Success message and token

    Raises:
        HTTPException: 400 if email already exists
    """
    # Check if user already exists
    existing_user = await session.execute(
        select(User).where(User.email == email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = pwd_context.hash(password)

    # Create new user
    user = User(
        email=email,
        name=name,
        hashed_password=hashed_password,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create JWT token
    access_token = create_access_token(user_id=user.id)

    return {
        "message": "User registered successfully",
        "user_id": str(user.id),
        "email": user.email,
        "token": access_token,
    }


@router.post("/login")
async def login(
    request: Request,
    email: str,
    password: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Authenticate user and return JWT token.

    Args:
        request: HTTP request object
        email: User's email address
        password: User's password
        session: Database session

    Returns:
        dict: User info and JWT token

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find user by email
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    access_token = create_access_token(user_id=user.id)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "token": access_token,
    }


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout endpoint (stateless - no server-side session to clear).

    Args:
        credentials: Bearer token (for validation only)

    Returns:
        dict: Success message
    """
    # In a JWT stateless system, logout is client-side only
    # We just verify the token is valid
    token = credentials.credentials
    verify_token(token)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get current user information.

    Args:
        credentials: Bearer token
        session: Database session

    Returns:
        dict: User information
    """
    token = credentials.credentials
    user_id = verify_token(token)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }