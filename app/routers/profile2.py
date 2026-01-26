from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from app.db import get_session
from app.models.model import Profile
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
    
    if resume_key == null:
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