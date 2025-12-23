from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

from app.db import get_session
from app.models.model import Profile
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    username: str | None = None
    bio: str | None = None
    location: str | None = None


@router.get("/")
async def get_profile(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    profile = await session.get(Profile, user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/")
async def update_profile(
    update: ProfileUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    profile = await session.get(Profile, user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for k, v in update.dict(exclude_unset=True).items():
        setattr(profile, k, v)

    session.add(profile)
    await session.commit()
    return profile
