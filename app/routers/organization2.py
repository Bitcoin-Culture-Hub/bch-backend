from cProfile import Profile
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from app.db import get_session
from ..models.model import OpportunityCategory, Organization, OrganizationMember, OrganizationRead,Opportunity,Application
from app.services.auth_service import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/org", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str
    type: str | None = None
    location: str | None = None
    email: str | None = None
    description: str | None = None
    
    
class OrgUpdate(BaseModel):
    name: str
    type: str | None = None
    location: str | None = None
    email: str | None = None
    description: str | None = None

async def ensure_member(org_id: str, user_id: str, session: AsyncSession):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if not result.first():
        raise HTTPException(403, "Not a member of this organization")

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

@router.get("/{org_id}/public")
async def get_org(
    org_id: str,
    session: AsyncSession = Depends(get_session),
):
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    
    # filter 
    # get all corresponding opportunities for the org
    
    return org



@router.patch("/{org_id}", response_model=OrganizationRead)
async def edit_organizations(
    org_id: str,
    data: OrgUpdate,
    session: AsyncSession = Depends(get_session),
):
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    await session.commit()
    await session.refresh(org)

    return OrganizationRead.from_orm(org)


@router.get("/{org_id}/members")
async def list_members(
    org_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    result = await session.exec(
        select(OrganizationMember, Profile)
        .join(Profile, Profile.user_id == OrganizationMember.user_id)
        .where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.deleted_at.is_(None)
        )
    )

    rows = result.all()

    return [
        {
            "user_id": member.user_id,
            "role": member.role,
            "joined_at": member.joined_at,
            "profile": {
                "username": profile.username,
                "bio": profile.bio,
                "location": profile.location,
                "profile_picture": profile.profile_picture,
            }
        }
        for member, profile in rows
    ]

@router.delete("/{org_id}")
async def delete_organization(org_id: str, session: AsyncSession = Depends(get_session)):
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    now = datetime.utcnow()
    
    org.deleted_at = now
    session.add(org)

    org_members_stmt = select(OrganizationMember).where(OrganizationMember.org_id == org_id)
    org_members: List[OrganizationMember] = session.exec(org_members_stmt).all()
    for member in org_members:
        member.deleted_at = now
        session.add(member)
    
    opp_stmt = select(Opportunity).where(Opportunity.org_id == org_id)
    opportunities: List[Opportunity] = session.exec(opp_stmt).all()
    
    for opp in opportunities:
        app_stmt = select(Application).where(Application.opportunity_id == opp.id)
        applications: List[Application] = session.exec(app_stmt).all()
        for app in applications:
            app.deleted_at = now
            session.add(app)
        
        cat_stmt = select(OpportunityCategory).where(OpportunityCategory.opportunity_id == opp.id)
        categories: List[OpportunityCategory] = session.exec(cat_stmt).all()
        for cat in categories:
            cat.deleted_at = now
            session.add(cat)
        
        opp.deleted_at = now
        session.add(opp)
    
    session.commit()
    
    return {"message": f"Organization {org.name} and all related data have been soft-deleted."}