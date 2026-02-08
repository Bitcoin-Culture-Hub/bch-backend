from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from fastapi import Depends, HTTPException, status
from app.db import get_session
from ..models.model import OpportunityCategory, Organization, OrganizationMember, OrganizationRead,Opportunity,Application, OrganizationPrompts, Profile
from app.services.auth_service import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/org", tags=["organizations"])

class AddMemberRequest(BaseModel):
    user_id: str
    role: str

class RemoveMemberRequest(BaseModel):
    user_id: str
    
    
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

class OrgPromptUpdate(BaseModel):
    prompt_key: str
    custom_text: str
    
class OrgPromptUpdateList(BaseModel):
    prompts: List[OrgPromptUpdate]



async def ensure_member(org_id: str, user_id: str, session: AsyncSession):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if not result.first():
        raise HTTPException(403, "Not a member of this organization")
    
async def ensure_org_owner(
    org_id: str,
    user_id: str,
    session: AsyncSession,
):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.role.lower() == "owner",
        )
    )

    if not result.first():
        raise HTTPException(
            status_code=403,
            detail="Only organization owners can perform this action",
        )
    
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
        .where(OrganizationMember.user_id == user["user_id"],Organization.deleted_at.is_(None))
    )

    return result.all()

@router.get("/owned-orgs")
async def owned_orgs(
        user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(Organization)
        .join(OrganizationMember, OrganizationMember.org_id == Organization.id)
        .where(
            OrganizationMember.user_id == user["user_id"],
            OrganizationMember.role == "owner"
        )
    )

    result = await session.exec(stmt)
    orgs = result.all()
    return orgs


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
    session: AsyncSession = Depends(get_session),
):

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
            "username": profile.username,
            "bio": profile.bio,
            "location": profile.location,
            "profile_picture": profile.profile_picture,
        }
        for member, profile in rows
    ]
    
    
@router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: str,
    payload: AddMemberRequest,
    session: AsyncSession = Depends(get_session),
):
    print(payload)
    existing = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == payload.user_id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    member = OrganizationMember(
        org_id=org_id,
        user_id=payload.user_id,
        role=payload.role,
    )

    session.add(member)
    await session.commit()
    await session.refresh(member)

    return {
        "user_id": member.user_id,
        "role": member.role,
        "joined_at": member.joined_at,
    }
    

@router.delete("/{org_id}/members", status_code=status.HTTP_200_OK)
async def remove_member(
    org_id: str,
    payload: RemoveMemberRequest,
    session: AsyncSession = Depends(get_session),
):
    # Check if member exists
    existing_member = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == payload.user_id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    
    member = existing_member.first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization",
        )

    member.deleted_at = datetime.utcnow()

    session.add(member)
    await session.commit()
    await session.refresh(member)

    return {"message": f"User {member.user_id} removed from organization {org_id}"}
    
@router.patch("/{org_id}/archive")
async def archive_organization(
    org_id: str,
    session: AsyncSession = Depends(get_session)
):
    now = datetime.utcnow()

    async with session.begin():
        org = await session.get(Organization, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        if org.deleted_at is not None:
            raise HTTPException(
                status_code=400,
                detail="Organization already archived"
            )

        org.deleted_at = now
        session.add(org)

        members = await session.exec(
            select(OrganizationMember).where(OrganizationMember.org_id == org_id)
        )
        for member in members.all():
            member.deleted_at = now

        opps = await session.exec(
            select(Opportunity).where(Opportunity.org_id == org_id)
        )
        opportunities = opps.all()

        for opp in opportunities:
            apps = await session.exec(
                select(Application).where(Application.opportunity_id == opp.id)
            )
            for app in apps.all():
                app.deleted_at = now

            cats = await session.exec(
                select(OpportunityCategory).where(
                    OpportunityCategory.opportunity_id == opp.id
                )
            )
            for cat in cats.all():
                cat.deleted_at = now

            opp.deleted_at = now

    return {
        "message": f"Organization {org.name} and all related data archived successfully"
    }



@router.patch("/{org_id}/unarchive")
async def unarchive_organization(
    org_id: str,
    session: AsyncSession = Depends(get_session)
):
    async with session.begin():
        org = await session.get(Organization, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        if org.deleted_at is None:
            raise HTTPException(status_code=400, detail="Organization is not archived")

        org.deleted_at = None

        members_result = await session.exec(
            select(OrganizationMember).where(OrganizationMember.org_id == org_id)
        )
        for member in members_result.all():
            member.deleted_at = None

        opps_result = await session.exec(
            select(Opportunity).where(Opportunity.org_id == org_id)
        )
        opportunities = opps_result.all()

        for opp in opportunities:
            apps_result = await session.exec(
                select(Application).where(Application.opportunity_id == opp.id)
            )
            for app in apps_result.all():
                app.deleted_at = None

            cats_result = await session.exec(
                select(OpportunityCategory).where(
                    OpportunityCategory.opportunity_id == opp.id
                )
            )
            for cat in cats_result.all():
                cat.deleted_at = None

            opp.deleted_at = None

    return {
        "message": f"Organization {org.name} has been unarchived."
    }
@router.get("/{org_id}/prompts")
async def get_org_prompts(
    org_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    result = await session.exec(
        select(OrganizationPrompts).where(
            OrganizationPrompts.organization_id == org_id
        )
    )
    prompts: list[OrganizationPrompts] = result.all()
    print(prompts)
    if not prompts:
        default_prompts = [
            {"prompt_key": "what_it_is", "custom_text": "What It Is"},
            {"prompt_key": "who_its_for", "custom_text": "Who It's For"},
            {"prompt_key": "why_it_exists", "custom_text": "Why It Exists"},
            {"prompt_key": "how_it_operates", "custom_text": "How It Operates"},
        ]
        return default_prompts

    return [
        {"prompt_key": p.prompt_key, "custom_text": p.custom_text}
        for p in prompts
    ]


@router.put("/{org_id}/prompts")
async def upsert_org_prompts(
    org_id: str,
    data: OrgPromptUpdate | OrgPromptUpdateList, 
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    # Normalize input to a list
    if isinstance(data, OrgPromptUpdateList):
        prompts_to_upsert = data.prompts 
    else:
        prompts_to_upsert = [data]

    for p in prompts_to_upsert:
        result = await session.exec(
            select(OrganizationPrompts).where(
                OrganizationPrompts.organization_id == org_id,
                OrganizationPrompts.prompt_key == p.prompt_key,
            )
        )
        prompt = result.first()

        if prompt:
            prompt.custom_text = p.custom_text
        else:
            prompt = OrganizationPrompts(
                organization_id=org_id,
                prompt_key=p.prompt_key,
                custom_text=p.custom_text,
            )
            session.add(prompt)

    await session.commit()
    return {"message": "Prompt(s) saved"}



@router.get("/{org_id}/is-owner")
async def is_org_owner(
    org_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user["user_id"],
            OrganizationMember.role.lower() == "owner",
        )
    )

    return {
        "is_owner": result.first() is not None
    }