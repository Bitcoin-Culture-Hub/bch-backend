from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
import uuid
from ..models.model import Organization, OrganizationMember, OpportunityCategory, Opportunity,Application,OpportunityRead
from ..db import get_session
from ..services.auth_service import get_current_user
router = APIRouter(
    prefix="/org/{org_id}/opportunities",
    tags=["opportunities"]
)
class OpportunityCreate(BaseModel):
    title: str
    type: str | None = None
    description: str | None = None
    location: str | None = None
    timeCommitment: str | None = None
    categories: List[str] | None = None

class OpportunityUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    location: str | None = None
    time_commitment: str | None = None
    categories: List[str] | None = None
    
class ApplyRequest(BaseModel):
    email: str
    username: str
    location: str | None = None
    avatar: str | None = None
    status:str
class ApplicationRead(BaseModel):
    id: str
    opportunity_id: str
    user_id: str
    applied_at: datetime

    email: Optional[str]
    username: Optional[str]
    location: Optional[str]
    avatar: Optional[str]
    status: Optional[str]

    class Config:
        orm_mode = True
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
async def create_opportunity(
    org_id: str,
    data: OpportunityCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    opp = Opportunity(
        id=str(uuid.uuid4()),
        org_id=org_id,
        title=data.title,
        type=data.type,
        description=data.description,
        location=data.location,
        time_commitment=data.timeCommitment,
        created_at=datetime.utcnow(),
        created_by=user["user_id"],
    )

        
    session.add(opp)
    categories = data.categories
    for category in categories:
        session.add(OpportunityCategory(opp.id,category))
        
    await session.commit()
    return opp


@router.get("/", response_model=list[OpportunityRead])
async def list_opportunities(
    org_id: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(
            Opportunity,
            Organization.name.label("org_name")
        )
        .join(Organization, Organization.id == Opportunity.org_id)
        .where(Opportunity.org_id == org_id)
    )

    results = await session.exec(stmt)
    opportunities_with_org = results.all()

    final_list = []
    for opportunity, org_name in opportunities_with_org:
        cat_stmt = select(OpportunityCategory.category).where(
            OpportunityCategory.opportunity_id == opportunity.id
        )
        categories_result = await session.exec(cat_stmt)
        categories = [c[0] for c in categories_result.all()]
        final_list.append(
            OpportunityRead(
                **opportunity.dict(),
                org_name=org_name,
                categories=categories
            )
        )
    return final_list



@router.patch(
    "/{opp_id}",
    response_model=OpportunityRead
)
async def patch_opportunity(
    org_id: str,
    opp_id: str,
    data: OpportunityUpdate,
    session: AsyncSession = Depends(get_session),
):
    opportunity = await session.get(Opportunity, opp_id)

    if not opportunity or opportunity.org_id != org_id:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    update_data = data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field != "categories":
            setattr(opportunity, field, value)

    if "categories" in update_data:
        new_categories = update_data["categories"]

        await session.execute(
            delete(OpportunityCategory).where(
                OpportunityCategory.opportunity_id == opp_id
            )
        )

        session.add_all(
            OpportunityCategory(opportunity_id=opp_id, category=cat)
            for cat in new_categories
        )
    await session.commit()
    await session.refresh(opportunity)

    stmt = (
        select(
            Opportunity,
            Organization.name.label("org_name")
        )
        .join(Organization, Organization.id == Opportunity.org_id)
        .where(Opportunity.id == opp_id)
    )

    result = await session.exec(stmt)
    opportunity, org_name = result.one()

    cat_stmt = select(OpportunityCategory.category).where(
    OpportunityCategory.opportunity_id == opp_id
)
    categories_result = await session.exec(cat_stmt)
    categories = [c[0] for c in categories_result.all()]  

    return OpportunityRead(
        **opportunity.dict(),
        org_name=org_name,
        categories=categories
    )

@router.get("/{opp_id}", response_model=OpportunityRead)
async def get_opportunity(
    opp_id: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Opportunity, Organization.name.label("org_name"))
        .join(Organization, Organization.id == Opportunity.org_id)
        .where(Opportunity.id == opp_id)
    )
    result = await session.exec(stmt)
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity, org_name = row

    cat_stmt = select(OpportunityCategory.category).where(
        OpportunityCategory.opportunity_id == opportunity.id
    )
    categories_result = await session.exec(cat_stmt)
    categories = categories_result.all()

    return OpportunityRead(
        **opportunity.dict(),
        org_name=org_name,
        categories=categories
    )


@router.post("/{opp_id}/apply")
async def apply(
    org_id: str,
    opp_id: str,
    data: ApplyRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    application = Application(
        opportunity_id=opp_id,
        user_id=user["user_id"],
        email=data.email,
        username=data.username,
        location=data.location,
        avatar=data.avatar,
        applied_at=datetime.utcnow(),
        status=data.status
    )

    session.add(application)
    try:
        await session.commit()
    except Exception:
        raise HTTPException(400, "Already applied")

    return {"message": "Application submitted"}


@router.get("/{opp_id}/applicants",response_model=List[ApplicationRead])
async def list_applicants(
    org_id: str,
    opp_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    result = await session.exec(
        select(Application).where(Application.opportunity_id == opp_id)
    )
    apps = result.scalars().all()
    return apps
