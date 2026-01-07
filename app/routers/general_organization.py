from collections import defaultdict
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from boto3.dynamodb.conditions import Key,Attr
from pydantic import BaseModel

from ..services.auth_service import get_current_user
from ..models.model import OpportunityCategory, OpportunityRead, Organization,Opportunity
import boto3
import os
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from ..services.auth_service import get_current_user
from app.db import get_session
from ..models.model import OrganizationMember, Application
router = APIRouter(prefix="/general", tags=["organizations"])


class ApplicationRead(SQLModel):
    id: str
    opportunity_id: str
    user_id: str
    applied_at: datetime
    email: Optional[str]
    username: Optional[str]
    location: Optional[str]
    avatar: Optional[str]
    status: Optional[str]
    opportunity_name: Optional[str]
    opportunity_type:Optional[str]
    class Config:
        orm_mode = True


@router.get("/orgs")
async def my_orgs(
    session: AsyncSession = Depends(get_session)
):
    print(session)
    result = await session.exec(
        select(Organization)
    )
    print(result,'print statememt')
    return result.all()


@router.get("/opportunity", response_model=List[OpportunityRead])
async def all_opportunities(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Opportunity, Organization.name.label("org_name"))
        .join(Organization, Organization.id == Opportunity.org_id)
    )
    results = await session.exec(stmt)
    opportunities_with_org = results.all()

    stmt_cats = select(OpportunityCategory)
    cats_result = await session.exec(stmt_cats)
    all_cats = cats_result.all()

    cats_map = defaultdict(list)
    for oc in all_cats:
        cats_map[oc.opportunity_id].append(oc.category)

    final_list = []
    for opp, org_name in opportunities_with_org:
        categories = cats_map.get(opp.id, [])
        final_list.append(
            OpportunityRead(
                **opp.dict(),
                org_name=org_name,
                categories=categories
            )
        )

    return final_list


@router.get("/myapplications", response_model=List[ApplicationRead])
async def user_applicants(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    user_id = user["user_id"]

    # Select Application + Opportunity title and type
    stmt = (
        select(
            Application,
            Opportunity.title.label("opportunity_name"),
            Opportunity.type.label("opportunity_type")
        )
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .where(Application.user_id == user_id)
    )

    result = await session.exec(stmt)

    return [
        ApplicationRead(
            **application.dict(),
            opportunity_name=opportunity_name,
            opportunity_type=opportunity_type
        )
        for application, opportunity_name, opportunity_type in result.all()
    ]