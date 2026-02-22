from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from app.db import get_session
from app.models.model import Application, InterviewSlot, Opportunity, Organization, OrganizationMember, Profile
from app.services.auth_service import get_current_user
import boto3, uuid
import os
import re
router = APIRouter(prefix="/profile", tags=["profile"])

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ["BITCOIN_AWS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["BITCOIN_AWS_SECRET_ACCESS_KEY"],
    region_name="us-east-2"
)
BUCKET_NAME = 'bitcoin-culture-hub-resumes'

class ProfileUpdate(BaseModel):
    username: str | None = None
    bio: str | None = None
    location: str | None = None
    resume_link :Optional[str]

class ReadInterviewRequest(BaseModel):
    slot_id:str
    org_id:str
    

async def ensure_member(org_id: str, user_id: str, session: AsyncSession):
    result = await session.exec(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if not result.first():
        raise HTTPException(403, "Not a member of this organization")

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

@router.post("/upload-resume")
async def upload_resume(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    print(file, ' is the file')
    user_id = user["user_id"]
    
    original = file.filename 

    cleaned_name = re.sub(r"[.\s]", "", re.sub(r"\.[^.]+$", "", original))

    file_key = f"{cleaned_name}_{uuid.uuid4()}.pdf"

    content = await file.read()

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=file_key,
        Body=content,
        ContentType="application/pdf"
    )

    result = await session.exec(
        select(Profile).where(Profile.user_id == user_id)
    )
    profile = result.one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.resume_link = file_key

    session.add(profile)
    await session.commit()

    return {
        "ok": True,
        "resume_file": file_key,
        "message": "Resume uploaded successfully"
    }
@router.get("/resume/preview")
async def preview_resume(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    user_id = user["user_id"]

    result = await session.exec(
        select(Profile).where(Profile.user_id == user_id)
    )
    profile = result.one_or_none()

    if not profile or not profile.resume_link:
        raise HTTPException(status_code=404, detail="Resume not found")

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": profile.resume_link,
            "ResponseContentDisposition": "inline",
            "ResponseContentType": "application/pdf"
        },
        ExpiresIn=3600  
    )

    return {
        "preview_url": presigned_url
    }

@router.get("/applications/resume-url/{resume_key}")
async def get_resume_download_url(
    resume_key: str,
    # user=Depends(get_current_user),
):
    
    if resume_key == None:
        raise HTTPException(status_code=404, detail="Resume not found")

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": resume_key,
            "ResponseContentDisposition": "attachment",  
        },
        ExpiresIn=600 * 5, 
    )

    return {"url": url}


@router.patch("/select-time")
async def pick_interview_time(
    payload: ReadInterviewRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # ensure user is the admin for the organization
    # select the application that is being accepted
    # Check that the applicant has an application for this opportunity
    result = await session.exec(
        select(InterviewSlot).where(
            InterviewSlot.id == payload.slot_id,
        )
    )
    
    
    application = result.one()
    if not application:
        raise HTTPException(status_code=404, detail="interview time not found for this applicant")
    # get the opp id the job wants
    application.status = "booked"
    app_id = application.applicant_id 
    opp_id = application.opportunity_id
    others_result  = await session.exec(
        select(InterviewSlot).where(InterviewSlot.id != application.id, 
                                    InterviewSlot.applicant_id == app_id, 
                                    InterviewSlot.opportunity_id == opp_id)
        )
    for other in others_result.all():
        other.status = "cancelled"

    await session.commit()
    
    
@router.get("/my-interviews")
async def get_my_booked_interviews(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(Application.id).where(
            Application.user_id == user["user_id"],Application.deleted_at == None
        )
    )
    application_ids = result.all()

    if not application_ids:
        return []

    slots_result = await session.exec(
        select(InterviewSlot,Opportunity.title, Organization.name,Organization.meeting_link)
        .join(Opportunity, InterviewSlot.opportunity_id == Opportunity.id)
        .join(Organization,Opportunity.org_id == Organization.id)
        .where(
            InterviewSlot.applicant_id.in_(application_ids),
            InterviewSlot.status == "booked"
        ).order_by(InterviewSlot.interview_datetime)
    )

    booked_slots = slots_result.all()
    return [
        {
            **slot.model_dump(),
            "opportunity_title": title,
            "org_name": org_name,
            "meeting_link":meeting_link
        }
        for slot, title, org_name,meeting_link in booked_slots
    ]


@router.get("/pending-selection")
async def get_pending_interview_slots(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all interview slots where the user needs to select a time (status: pending)"""
    result = await session.exec(
        select(Application.id).where(
            Application.user_id == user["user_id"],Application.deleted_at == None 
        )
    )
    application_ids = result.all()

    if not application_ids:
        return []

    slots_result = await session.exec(
        select(InterviewSlot, Opportunity.title, Organization.name)
        .join(Opportunity, InterviewSlot.opportunity_id == Opportunity.id)
        .join(Organization, Opportunity.org_id == Organization.id)
        .where(
            InterviewSlot.applicant_id.in_(application_ids),
            InterviewSlot.status == "pending"
        )
        .order_by(InterviewSlot.interview_datetime)
    )

    pending_slots = slots_result.all()

    return [
        {
            **slot.model_dump(),
            "opportunity_title": title,
            "org_name": org_name,
        }
        for slot, title, org_name in pending_slots
    ]