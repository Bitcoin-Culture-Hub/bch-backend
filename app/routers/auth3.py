from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession
import secrets
import boto3
import os
from typing import List, Optional
from app.db import get_session
from app.models.model import User, Profile, OrganizationMember
from app.services.password import hash_password, verify_password
from app.services.auth_service import create_access_token
from app.services.auth_service import get_current_user_optional

router = APIRouter(prefix="/authorize", tags=["auth"])


class OrgInvite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: str
    role: str
    token: str
    # used: bool = False changed
    expires_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    invite_token: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class InviteCreateRequest(BaseModel):
    org_id: str
    role: str
    expires_in_hours: Optional[int] = 24

class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "passwordresettoken"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    token: str = Field(index=True)
    expires_at: datetime

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

RESET_TOKEN_EXPIRE_MINUTES = 30
SENDER_EMAIL = "noreply@bitcoinculturehub.com"

ses_client = boto3.client(
    "ses",
    region_name="us-east-2",
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY"),
)


@router.post("/invite/create")
async def create_invite(data: InviteCreateRequest, session: AsyncSession = Depends(get_session)):
    token = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(hours=data.expires_in_hours)
    invite = OrgInvite(
        org_id=data.org_id,
        role=data.role,
        token=token,
        expires_at=expires_at,
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    link = f"https://www.bitcoinculturehub.com/auth?token={invite.token}"
    return {"invite_link": link, "expires_at": invite.expires_at}


@router.get("/invite/accept")
async def accept_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user_optional),
):
    invite = (await session.exec(select(OrgInvite).where(OrgInvite.token == token))).first()
    if not invite:
        raise HTTPException(404, "Invalid invite")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invite expired")

    if user:
        session.add(OrganizationMember(org_id=invite.org_id, user_id=user["user_id"], role=invite.role))

        await session.commit()
        return {"ok": True, "org_id": invite.org_id}

    return {"action": "SIGNUP_REQUIRED", "invite_token": token}

@router.post("/signup")
async def signup(user: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = (await session.exec(select(User).where(User.email == user.email))).first()
    if existing:
        raise HTTPException(409, "Email already registered")

    invite = None

    if user.invite_token:
        invite = (await session.exec(select(OrgInvite).where(OrgInvite.token == user.invite_token))).first()
        if not invite: raise HTTPException(400, "Invalid invite")
        if invite.expires_at < datetime.utcnow(): raise HTTPException(400, "Invite expired")

    db_user = User(email=user.email, hashed_password=hash_password(user.password))
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    session.add(Profile(user_id=db_user.id, username=user.username))

    if invite:
        session.add(OrganizationMember(org_id=invite.org_id, user_id=db_user.id, role=invite.role))
        session.add(invite)

    await session.commit()
    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "user_id": db_user.id, "org_id": invite.org_id if invite else None}


@router.post("/login")
async def login(data: UserLogin, session: AsyncSession = Depends(get_session)):
    user = (await session.exec(select(User).where(User.email == data.email))).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    profile = await session.get(Profile, user.id)
    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "user_id": user.id,
        "email": user.email,
        "username": profile.username,
        "bio": profile.bio,
        "location": profile.location,
        "profile_picture": profile.profile_picture,
    }



@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)):
    user = (await session.exec(select(User).where(User.email == data.email))).first()

    if user:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        session.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at))
        await session.commit()

        reset_link = f"https://www.bitcoinculturehub.com/reset-password?token={token}"
        raw_email = f"""From: Bitcoin Culture Hub <{SENDER_EMAIL}>
To: {user.email}
Subject: Reset your password
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8

<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <h2 style="color: #F7931A;">Reset Your Password</h2>
    <p>We received a request to reset your password. Click the button below to set a new one.</p>
    <p>This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
    <a href="{reset_link}"
       style="background:#F7931A;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
      Reset Password
    </a>
    <p>If you didn't request this, you can safely ignore this email.</p>
    <br/>
    <img src="https://i.imgur.com/GtE82qY.png" alt="Bitcoin Culture Hub" style="width:70%;max-width:500px;margin-top:20px;" />
  </body>
</html>"""

        try:
            ses_client.send_raw_email(
                RawMessage={"Data": raw_email},
                Source=SENDER_EMAIL,
                Destinations=[user.email],
            )
        except Exception as e:
            print(f"SES error: {e}")

    # Always return 200 — don't reveal whether the email exists
    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, session: AsyncSession = Depends(get_session)):
    reset_token = (
        await session.exec(select(PasswordResetToken).where(PasswordResetToken.token == data.token))
    ).first()

    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired reset link.")

    user = await session.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(404, "User not found.")

    user.hashed_password = hash_password(data.new_password)
    session.add(user)
    await session.delete(reset_token)
    await session.commit()

    return {"message": "Password updated successfully."}
