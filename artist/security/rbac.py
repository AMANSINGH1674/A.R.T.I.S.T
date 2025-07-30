"""
Role-Based Access Control (RBAC) implementation.
"""

from typing import Dict, Any, List, Optional
from functools import wraps
from fastapi import HTTPException, status, Depends

from ..security.auth import get_current_user


class Role:
    """Defines user roles"""
    ADMIN = "admin"
    ENGINEER = "engineer"
    BUSINESS_USER = "business_user"
    GUEST = "guest"


ROLES_HIERARCHY = {
    Role.ADMIN: [Role.ENGINEER, Role.BUSINESS_USER, Role.GUEST],
    Role.ENGINEER: [Role.BUSINESS_USER, Role.GUEST],
    Role.BUSINESS_USER: [Role.GUEST],
    Role.GUEST: []
}


def has_permission(user_roles: List[str], required_roles: List[str]) -> bool:
    """Check if user has required roles"""
    for user_role in user_roles:
        if user_role in required_roles:
            return True
        # Check hierarchy
        for required_role in required_roles:
            if required_role in ROLES_HIERARCHY.get(user_role, []):
                return True
    return False


def require_roles(required_roles: List[str]):
    """Decorator to enforce role-based access control"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                # Attempt to get from dependencies
                for arg in args:
                    if isinstance(arg, dict) and "username" in arg:
                        current_user = arg
                        break
            
            if not current_user or not has_permission(current_user.get("roles", []), required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
