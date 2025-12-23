from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, EmailStr

from app.db import get_session
from app.models.model import User, Profile

from app.services.password import hash_password, verify_password
from app.services.auth_service import create_access_token

router = APIRouter(prefix="/authorize", tags=["auth"])


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
async def signup(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # Check email
    result = await session.exec(select(User).where(User.email == user.email))
    if result.first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    db_user = User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    session.add(db_user)
    await session.commit()        
    await session.refresh(db_user)  

    # Create profile AFTER user exists
    db_profile = Profile(
        user_id=db_user.id,
        username=user.username
    )

    session.add(db_profile)
    await session.commit()

    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "user_id": db_user.id}


@router.post("/login")
async def login(data: UserLogin, session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(User).where(User.email == data.email))
    user = result.first()
    print(user)
    print("LOGIN EMAIL:", data.email)
    print("USER FOUND:", bool(user))

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    valid = verify_password(data.password, user.hashed_password)
    print("PASSWORD VALID:", valid)

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    profile = await session.get(Profile, user.id)
    token = create_access_token({"sub": user.id})

    return {
        "access_token": token,
        "user_id": user.id,
        "email": user.email,
        "username": profile.username,
        "bio": profile.bio,
        "location": profile.location,
        "profile_picture": profile.profile_picture,
    }
