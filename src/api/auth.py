"""
Authentication API endpoints for TodoApp Backend.
Fixed for JSON body requests (Frontend compatible).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from src.database import get_session
from src.middleware.auth import create_access_token, verify_token
from src.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ===============================
# Security
# ===============================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ===============================
# Request Schemas
# ===============================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ===============================
# Register
# ===============================
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        name=data.name,
        hashed_password=pwd_context.hash(data.password),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(user_id=user.id)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "token": token,
    }


# ===============================
# Login
# ===============================
@router.post("/login")
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(
        data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(user_id=user.id)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "token": token,
    }


# ===============================
# Logout
# ===============================
@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    verify_token(credentials.credentials)
    return {"message": "Logged out successfully"}


# ===============================
# Current User
# ===============================
@router.get("/me")
async def me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
):
    user_id = verify_token(credentials.credentials)

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
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
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
