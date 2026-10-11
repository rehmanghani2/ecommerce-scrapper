"""
Admin and User Management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets

from app.models.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.product import Product
from app.api.routes.auth import get_current_user, create_access_token
from app.config import settings

router = APIRouter()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


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
    api_key: Optional[str] = None
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    job_count: int = 0
    total_products_scraped: int = 0

    class Config:
        from_attributes = True


class UserJobItem(BaseModel):
    id: int
    job_id: str
    name: str
    url: str
    domain: str
    status: str
    job_type: str
    total_products: int
    scraped_pages: int
    total_pages: int
    progress: float
    user_id: Optional[int] = None
    username: Optional[str] = None
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    api_key: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    stats: Dict[str, Any]
    jobs: List[UserJobItem]

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
            detail="Admin privileges required. Access denied."
        )
    return current_user


@router.post("/login")
async def admin_login(
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Dedicated Admin Login endpoint.
    Strictly verifies user credentials AND requires is_superuser == True.
    Non-superusers receive 403 Forbidden.
    """
    query = select(User).where((User.username == payload.username) | (User.email == payload.username))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.verify_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect administrator username or password"
        )

    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This account does not have administrator privileges."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is currently suspended."
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    user.last_login = datetime.utcnow()
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": True,
            "is_active": True
        }
    }


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
        # Match explicit user jobs, or for user 1 include legacy null user_id jobs
        job_filter = Job.user_id == u.id if u.id != 1 else or_(Job.user_id == u.id, Job.user_id.is_(None))
        j_count = (await db.execute(select(func.count(Job.id)).where(job_filter))).scalar() or 0
        p_count = (await db.execute(select(func.sum(Job.total_products)).where(job_filter))).scalar() or 0

        user_items.append(
            AdminUserItem(
                id=u.id,
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                is_active=bool(u.is_active),
                is_superuser=bool(u.is_superuser),
                api_key=u.api_key,
                created_at=u.created_at,
                last_login=u.last_login,
                job_count=j_count,
                total_products_scraped=int(p_count or 0),
            )
        )

    return user_items


@router.get("/users/{user_id}/details", response_model=UserDetailResponse)
async def get_user_full_details(
    user_id: int,
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get deep details for a user: profile, timestamps, aggregated stats,
    and the complete list of scraping jobs they created.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job_filter = Job.user_id == user_id if user_id != 1 else or_(Job.user_id == user_id, Job.user_id.is_(None))
    stmt = select(Job).where(job_filter).order_by(Job.id.desc())
    jobs_res = await db.execute(stmt)
    jobs = jobs_res.scalars().all()

    # Aggregate stats
    total_jobs = len(jobs)
    completed_jobs = sum(1 for j in jobs if str(j.status).lower() in ("completed", "jobstatus.completed"))
    failed_jobs = sum(1 for j in jobs if str(j.status).lower() in ("failed", "jobstatus.failed"))
    running_jobs = sum(1 for j in jobs if str(j.status).lower() in ("running", "jobstatus.running"))
    total_products = sum(j.total_products or 0 for j in jobs)
    total_pages = sum(j.scraped_pages or 0 for j in jobs)
    unique_domains = sorted(list(set(j.domain for j in jobs if j.domain)))

    job_items = []
    for j in jobs:
        dur = None
        if j.started_at and j.completed_at:
            dur = (j.completed_at - j.started_at).total_seconds()

        job_items.append(
            UserJobItem(
                id=j.id,
                job_id=j.job_id,
                name=j.name,
                url=j.url,
                domain=j.domain,
                status=str(j.status.value if hasattr(j.status, 'value') else j.status),
                job_type=str(j.job_type.value if hasattr(j.job_type, 'value') else j.job_type),
                total_products=j.total_products or 0,
                scraped_pages=j.scraped_pages or 0,
                total_pages=j.total_pages or 0,
                progress=float(j.progress or 0.0),
                user_id=user.id,
                username=user.username,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                duration=dur,
                error_message=j.error_message,
            )
        )

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        is_superuser=bool(user.is_superuser),
        api_key=user.api_key,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        stats={
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": running_jobs,
            "total_products": total_products,
            "total_pages": total_pages,
            "unique_domains": unique_domains,
            "success_rate": round((completed_jobs / total_jobs) * 100, 1) if total_jobs > 0 else 0,
        },
        jobs=job_items,
    )


@router.get("/jobs", response_model=Dict[str, Any])
async def list_all_platform_jobs(
    status_filter: Optional[str] = None,
    user_id_filter: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """List all jobs across all users on the platform with search & filters."""
    query = select(Job).order_by(Job.id.desc())

    if status_filter and status_filter.lower() != 'all':
        query = query.where(Job.status == status_filter.lower())

    if user_id_filter is not None:
        if user_id_filter == 1:
            query = query.where(or_(Job.user_id == 1, Job.user_id.is_(None)))
        else:
            query = query.where(Job.user_id == user_id_filter)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.where(or_(Job.job_id.ilike(search_fmt), Job.name.ilike(search_fmt), Job.domain.ilike(search_fmt)))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(query)
    jobs = res.scalars().all()

    # Get users map
    user_ids = list(set(j.user_id for j in jobs if j.user_id))
    users_map = {}
    if user_ids:
        u_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_res.scalars().all():
            users_map[u.id] = u.username

    job_items = []
    for j in jobs:
        dur = None
        if j.started_at and j.completed_at:
            dur = (j.completed_at - j.started_at).total_seconds()

        job_items.append(
            UserJobItem(
                id=j.id,
                job_id=j.job_id,
                name=j.name,
                url=j.url,
                domain=j.domain,
                status=str(j.status.value if hasattr(j.status, 'value') else j.status),
                job_type=str(j.job_type.value if hasattr(j.job_type, 'value') else j.job_type),
                total_products=j.total_products or 0,
                scraped_pages=j.scraped_pages or 0,
                total_pages=j.total_pages or 0,
                progress=float(j.progress or 0.0),
                user_id=j.user_id,
                username=users_map.get(j.user_id, "demo" if (not j.user_id or j.user_id == 1) else f"user_{j.user_id}"),
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                duration=dur,
                error_message=j.error_message,
            )
        )

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total_count + page_size - 1) // page_size),
        "jobs": job_items,
    }


@router.get("/system/telemetry")
async def get_admin_system_telemetry(
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get system telemetry, proxy pool metrics, and infrastructure health."""
    from app.core.proxy_manager import build_proxy_pool
    pool = build_proxy_pool()
    proxy_status = pool.get_status_summary() if hasattr(pool, 'get_status_summary') else {}

    # DB metrics
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    job_count = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    product_count = (await db.execute(select(func.count(Product.id)))).scalar() or 0

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "connected": True,
            "engine": "PostgreSQL (Neon) / SQLite Async",
            "users_count": user_count,
            "jobs_count": job_count,
            "products_count": product_count,
        },
        "proxy_pool": {
            "total_proxies": proxy_status.get("total_proxies", 0),
            "healthy_proxies": proxy_status.get("healthy_proxies", 0),
            "banned_proxies": proxy_status.get("banned_proxies", 0),
            "failover_enabled": True,
        },
        "environment": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        }
    }


@router.post("/users/{user_id}/regenerate-api-key")
async def regenerate_user_api_key(
    user_id: int,
    admin: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate a new programmatic API key for a user account."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_key = f"sk_live_{secrets.token_hex(24)}"
    user.api_key = new_key
    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "message": f"Generated new API key for user @{user.username}",
        "api_key": new_key,
    }


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

    job_filter = Job.user_id == target_user.id if target_user.id != 1 else or_(Job.user_id == target_user.id, Job.user_id.is_(None))
    j_count = (await db.execute(select(func.count(Job.id)).where(job_filter))).scalar() or 0
    p_count = (await db.execute(select(func.sum(Job.total_products)).where(job_filter))).scalar() or 0

    return AdminUserItem(
        id=target_user.id,
        email=target_user.email,
        username=target_user.username,
        full_name=target_user.full_name,
        is_active=bool(target_user.is_active),
        is_superuser=bool(target_user.is_superuser),
        api_key=target_user.api_key,
        created_at=target_user.created_at,
        last_login=target_user.last_login,
        job_count=j_count,
        total_products_scraped=int(p_count or 0),
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
