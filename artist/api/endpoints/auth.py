"""
Authentication endpoints for ARTIST.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import structlog
from typing import Dict, Any

from ...security.auth import AuthManager

router = APIRouter()
logger = structlog.get_logger()
security = HTTPBearer()

# Global auth manager instance
auth_manager = AuthManager()

class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str
    expires_in: int

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return access token"""
    user = await auth_manager.authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "roles": user["roles"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60
    }

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    return await auth_manager.get_current_user(credentials.credentials)

@router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (invalidate token - in a real system, you'd maintain a blacklist)"""
    logger.info("User logged out", user=current_user["username"])
    return {"message": "Successfully logged out"}
