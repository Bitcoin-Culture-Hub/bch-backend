from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import EmailStr, BaseModel
from ..db import collection, waitlist
from .. import models, schemas, utils
from ..services.mailer import add_subscriber

# new changes
from typing import Union
import uuid
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from ..services.mailer import send_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


# ----------------------------------------
# Request Model
# ----------------------------------------
class ForgotPasswordRequest(BaseModel):
    email: str


# ----------------------------------------
# Forgot Password Route
# ----------------------------------------
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    # 1. Validate email format
    try:
        validate_email(request.email)
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    # 2. Check if user exists (SYNC)
    user = collection.find_one({"email": request.email})
    print("USER FOUND: ", user)
    # Do not reveal if user exists
    if not user:
        return {"message": "Password reset token has been sent (if a user exists)."}

    # 3. Generate token + expiration
    token = str(uuid.uuid4())
    expiration = datetime.utcnow() + timedelta(minutes=30)



    # 4. Save in DB (SYNC)
    collection.update_one(
        {"email": request.email},
        {
            "$set": {
                "reset_token": token,
                "reset_token_expires": expiration
            }
        }
    )
    
    result = collection.update_one(
    {"email": request.email},
    {"$set": {"reset_token": token, "reset_token_expires": expiration}}
    )
    print("UPDATE RESULT:", result.matched_count, result.modified_count)

    # 5. Send email (ASYNC function is okay to await)
    await send_reset_email(request.email, token)

    return {"message": "Password reset token has been sent (if a user exists)."}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    # 1. Find user with this token
    user = collection.find_one({"reset_token": request.token})

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # 2. Check expiration
    expires = user.get("reset_token_expires")
    if not expires or expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired. Please request a new reset link.")

    # 3. Hash new password
    hashed_password = utils.hash_password(request.new_password)

    # 4. Update password + delete token
    collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"hashed_password": hashed_password},
            "$unset": {"reset_token": "", "reset_token_expires": ""}
        }
    )

    return {"message": "Password has been reset successfully."}


# ----------------------------------------
# Signup
# ----------------------------------------
@router.post("/signup", response_model=schemas.RegisterToken, status_code=201)
async def signup(user: schemas.UserCreate):
    # email unique
    if collection.find_one({"email": user.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    # username unique
    if collection.find_one({"username": user.username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    hashed_password = utils.hash_password(user.password)

    user_doc = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "results": user.results or {}
    }

    result = collection.insert_one(user_doc)
    user_id = str(result.inserted_id)

    await add_subscriber(user_doc["email"])

    token = utils.create_access_token({"sub": str(user_id)})

    return {"access_token": token, "token_type": "bearer"}


# ----------------------------------------
# Join (Waitlist)
# ----------------------------------------
@router.post("/join", response_model=schemas.Token, status_code=201)
async def join(user: schemas.UserJoin):
    if waitlist.find_one({"email": user.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    user_doc = {"email": user.email}
    result = waitlist.insert_one(user_doc)

    await add_subscriber(user.email)

    token = utils.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# ----------------------------------------
# DummyLogin Model
# ----------------------------------------
class DummyLogin(BaseModel):
    email: EmailStr
    archetype: str | None = None


# ----------------------------------------
# Login
# ----------------------------------------
@router.post("/login", response_model=schemas.Token)
async def login(user: schemas.UserLogin):
    print(user)

    user_doc = collection.find_one({"email": user.email})
    print(user_doc)
    print("Email:", user.email)
    print("Password:", user.password)

    if user_doc:
        print("DB Hash:", user_doc.get("hashed_password"))
        print("Verify:", utils.verify_password(user.password, user_doc["hashed_password"]))

    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not utils.verify_password(user.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    try:
        await add_subscriber(user.email, user.archetype)
    except Exception as e:
        print(f"MailerLite failed: {e}")

    token = utils.create_access_token({"sub": str(user_doc['_id'])})

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user_doc["username"],
        "email": user_doc["email"]
    }
