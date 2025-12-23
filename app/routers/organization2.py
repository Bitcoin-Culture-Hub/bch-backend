from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from app.db import get_session
from ..models.model import Organization, OrganizationMember
from app.services.auth_service import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/org", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str
    type: str | None = None
    location: str | None = None
    email: str | None = None
    description: str | None = None


@router.post("/")
async def create_org(
    data: OrgCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    org = Organization(
        name=data.name,
        type=data.type,
        location=data.location,
        email=data.email,
        description=data.description,
        owner_id=user["user_id"],
        submitted_at=datetime.utcnow(),
    )

    member = OrganizationMember(
        org_id=org.id,
        user_id=user["user_id"],
        role="owner",
        joined_at=datetime.utcnow(),
    )

    session.add(org)
    session.add(member)
    await session.commit()
    return org


@router.get("/my")
async def my_orgs(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user["user_id"])
    )
    return result.all()


@router.get("/{org_id}")
async def get_org(
    org_id: str,
    session: AsyncSession = Depends(get_session),
):
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    return org


@router.get("/{org_id}/members")
async def list_members(
    org_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id
        )
    )
    return result.all()
