from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession
import secrets
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
    used: bool = False
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
    link = f"https://www.bitcoinculturehub.com//register?token={invite.token}"
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
    if invite.used:
        raise HTTPException(400, "Invite already used")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invite expired")

    if user:
        session.add(OrganizationMember(org_id=invite.org_id, user_id=user["user_id"], role=invite.role))
        invite.used = True
        await session.commit()
        return {"ok": True, "org_id": invite.org_id}

    return {"action": "SIGNUP_REQUIRED", "invite_token": token}

@router.post("/signup")
async def signup(user: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = (await session.exec(select(User).where(User.email == user.email))).first()
    if existing:
        raise HTTPException(409, "Email already registered")

    invite = None
    print(user, 'IS THE USER')
    if user.invite_token:
        invite = (await session.exec(select(OrgInvite).where(OrgInvite.token == user.invite_token))).first()
        if not invite: raise HTTPException(400, "Invalid invite")
        if invite.used: raise HTTPException(400, "Invite already used")
        if invite.expires_at < datetime.utcnow(): raise HTTPException(400, "Invite expired")

    db_user = User(email=user.email, hashed_password=hash_password(user.password))
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    session.add(Profile(user_id=db_user.id, username=user.username))

    if invite:
        session.add(OrganizationMember(org_id=invite.org_id, user_id=db_user.id, role=invite.role))
        invite.used = True
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
