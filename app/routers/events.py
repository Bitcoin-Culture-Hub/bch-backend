from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from app.db import get_session
from ..models.model import Organization, OrganizationMember, OrganizationRead,Bitcoin_Events
from app.services.auth_service import get_current_user
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlalchemy import func
from sqlmodel.ext.asyncio.session import AsyncSession


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/")
async def get_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size

    total = await session.scalar(
        select(func.count()).select_from(Bitcoin_Events)
    )

    # paginated query
    result = await session.execute(
        select(Bitcoin_Events)
        .order_by(Bitcoin_Events.start_date, Bitcoin_Events.id)
        .offset(offset)
        .limit(page_size)
    )

    events = result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "items": events,
    }