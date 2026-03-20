"""
Authentication endpoints for ARTIST.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import structlog
from typing import Dict, Any
from sqlalchemy.orm import Session

from ...security.auth import auth_manager, get_current_user
from ...database.session import get_db

router = APIRouter()
logger = structlog.get_logger()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str
    expires_in: int


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    user = await auth_manager.authenticate_user(request.username, request.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "roles": user["roles"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60,
    }


@router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (token invalidation requires a server-side blacklist in production)"""
    logger.info("User logged out", user=current_user["username"])
    return {"message": "Successfully logged out"}
