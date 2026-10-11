"""
Admin and User Management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.models.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.product import Product
from app.api.routes.auth import get_current_user

router = APIRouter()


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    full_name: Optional[str] = None


class AdminUserItem(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    job_count: int = 0

    class Config:
        from_attributes = True


class SystemOverview(BaseModel):
    total_users: int
    active_users: int
    superuser_count: int
    total_jobs: int
    total_products: int


async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the authenticated user is a superuser/admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/overview", response_model=SystemOverview)
async def get_admin_system_overview(
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide overview for admin."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_count = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    super_count = (await db.execute(select(func.count(User.id)).where(User.is_superuser == True))).scalar() or 0
    job_count = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    product_count = (await db.execute(select(func.count(Product.id)))).scalar() or 0

    return SystemOverview(
        total_users=user_count,
        active_users=active_count,
        superuser_count=super_count,
        total_jobs=job_count,
        total_products=product_count,
    )


@router.get("/users", response_model=List[AdminUserItem])
async def list_all_users(
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the system with their job counts and permissions."""
    result = await db.execute(select(User).order_by(User.id.asc()))
    users = result.scalars().all()

    user_items = []
    for u in users:
        j_count = (await db.execute(select(func.count(Job.id)).where(Job.user_id == u.id))).scalar() or 0
        user_items.append(
            AdminUserItem(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                is_active=bool(u.is_active),
                is_superuser=bool(u.is_superuser),
                created_at=u.created_at,
                last_login=u.last_login,
                job_count=j_count,
            )
        )

    return user_items


@router.patch("/users/{user_id}", response_model=AdminUserItem)
async def update_user_status(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Toggle user active status or superuser admin role."""
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.is_active is not None:
        target_user.is_active = payload.is_active
    if payload.is_superuser is not None:
        target_user.is_superuser = payload.is_superuser
    if payload.full_name is not None:
        target_user.full_name = payload.full_name

    await db.commit()
    await db.refresh(target_user)

    j_count = (await db.execute(select(func.count(Job.id)).where(Job.user_id == target_user.id))).scalar() or 0
    return AdminUserItem(
        id=target_user.id,
        email=target_user.email,
        username=target_user.username,
        full_name=target_user.full_name,
        is_active=bool(target_user.is_active),
        is_superuser=bool(target_user.is_superuser),
        created_at=target_user.created_at,
        last_login=target_user.last_login,
        job_count=j_count,
    )


@router.delete("/users/{user_id}")
async def delete_user_account(
    user_id: int,
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user account (admin cannot delete themselves)."""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(target_user)
    await db.commit()
    return {"success": True, "message": f"User {target_user.username} deleted"}
