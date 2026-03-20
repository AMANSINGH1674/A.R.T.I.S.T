"""
Authentication and authorization management for ARTIST.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog

from ..config import settings
from ..database.session import get_db
from ..database.models import User

logger = structlog.get_logger()



class AuthManager:
    """Manages authentication and authorization"""

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.access_token_expire_minutes

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    def get_password_hash(self, password: str) -> str:
        """Generate a password hash"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta if expires_delta else timedelta(minutes=self.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def health_check(self) -> bool:
        """Health check for the authentication manager"""
        return True

    async def authenticate_user(
        self, username: str, password: str, db: Session
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user against the database"""
        user: Optional[User] = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not user.is_active:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles or [],
            "is_superuser": user.is_superuser,
        }

    async def get_current_user(self, token: str, db: Session) -> Dict[str, Any]:
        """Get the current user from a JWT token, verified against the database"""
        payload = self.verify_token(token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user: Optional[User] = db.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles or [],
            "is_superuser": user.is_superuser,
        }


# Global auth manager instance for dependency injection
auth_manager = AuthManager()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """FastAPI dependency to get current user from JWT token"""
    return await auth_manager.get_current_user(credentials.credentials, db)
