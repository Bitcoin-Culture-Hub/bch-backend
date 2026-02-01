from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
import uuid
from ..models.model import Organization, OrganizationMember, OpportunityCategory, Opportunity,Application,OpportunityRead,Tools,OutputType,Profile
from ..db import get_session
from ..services.auth_service import get_current_user

BUCKET_NAME = 'bitcoin-culture-hub-resumes'


router = APIRouter(
    prefix="/org/{org_id}/opportunities",
    tags=["opportunities"]
)
class Location(BaseModel):
    type: str
    text: str | None = None
    
class OpportunityCreate(BaseModel):
    title: str
    type: str | None = None
    description: str | None = None
    location: Location | None = None
    time_commitment: str | None = None
    categories: List[str] | None = None
    skill_level:str|None = None
    estimated_hours:int|None = None
    due_date : str | None = None
    tools:List[str] | None = None
    output_type:List[str]| None = None
    
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
    resume_link: Optional[str]

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
        org_id=org_id,
        title=data.title,
        type=data.type,
        description=data.description,
        location=data.location.text if data.location else "Remote",
        time_commitment=data.time_commitment,
        skill_level=data.skill_level,
        estimated_hours=data.estimated_hours,
        due_date=data.due_date,
        created_at=datetime.utcnow(),
        created_by=user["user_id"],
    )

    session.add(opp)
    await session.flush()  # This ensures opp.id is available

    for category in data.categories or []:
        session.add(
            OpportunityCategory(
                opportunity_id=opp.id,
                category=category
            )
        )

    for tool in data.tools or []:
        session.add(
            Tools(
                opportunity_id=opp.id,
                tool_name=tool
            )
        )

    for output in data.output_type or []:
        session.add(
            OutputType(
                opportunity_id=opp.id,
                output_type=output
            )
        )
    await session.commit()
    await session.refresh(opp) 
    return opp


@router.delete("/{opportunity_id}")
async def delete_opportunity(
    org_id: str,
    opportunity_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    opp = await session.get(Opportunity, opportunity_id)

    if not opp or opp.org_id != org_id:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    await session.exec(
        delete(OpportunityCategory).where(
            OpportunityCategory.opportunity_id == opportunity_id
        )
    )
    await session.exec(
        delete(Tools).where(
            Tools.opportunity_id == opportunity_id
        )
    )
    await session.exec(
        delete(OutputType).where(
            OutputType.opportunity_id == opportunity_id
        )
    )

    await session.delete(opp)
    await session.commit()

    return {"detail": "Opportunity deleted successfully"}



# changed here 
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
        .where(Opportunity.org_id == org_id,Organization.deleted_at.is_(None))
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
    opp_id: str,
    data: ApplyRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    print(data,'running ')
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
    print(application)
    session.add(application)
    try:
        await session.commit()
    except Exception:
        raise HTTPException(400, "Already applied")

    return {"message": "Application submitted"}


@router.get("/{opp_id}/applicants", response_model=List[ApplicationRead])
async def list_applicants(
    org_id: str,
    opp_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await ensure_member(org_id, user["user_id"], session)

    result = await session.exec(
        select(Application, Profile.resume_link)
        .join(Profile, Profile.user_id == Application.user_id)
        .where(Application.opportunity_id == opp_id)
    )

    apps = []
    for app, resume_link in result.all():
        apps.append(
            ApplicationRead(
                **app.model_dump(),
                resume_link=resume_link
            )
        )

    return apps


