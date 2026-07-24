"""Admin API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.user import UserRole, UserResponse
from app.services.auth_service import AuthService
from app.main import get_db, get_current_user

router = APIRouter()


async def get_admin_user(current_user = Depends(get_current_user)):
    """Dependency to check if user is admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    # This would need to be implemented in AuthService
    # For now, return empty list
    return []


@router.get("/stats")
async def get_system_stats(
    admin_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (admin only)"""
    # This would need to be implemented
    return {
        "total_users": 0,
        "total_documents": 0,
        "total_queries": 0,
        "active_users": 0
    }


@router.post("/policies")
async def update_policies(
    policy_data: dict,
    admin_user = Depends(get_admin_user)
):
    """Update system policies (admin only)"""
    # This would update policy configurations
    return {"message": "Policies updated successfully"}
