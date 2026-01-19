from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List
from ..models.model import Profile
from app.services.auth_service import get_current_user
from app.db import get_session


router = APIRouter()

@router.get("/users", response_model=List[Profile])
async def get_all_users(
    session: AsyncSession = Depends(get_session),
):

    result = await session.exec(select(Profile))
    users = result.all()
    return users
