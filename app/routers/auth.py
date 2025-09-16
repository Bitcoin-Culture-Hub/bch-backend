from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import EmailStr, BaseModel
from ..db import collection, waitlist
from .. import models, schemas, utils
from ..services.mailer import add_subscriber

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=schemas.Token, status_code=201)
async def signup(user: schemas.UserCreate):
    # email unique
    if collection.find_one({"email": user.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Check if username exists
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

'''@router.post("/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.email == user.email).first()
    if not u or not utils.verify_password(user.password, u.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = utils.create_access_token({"sub": str(u.id)})
    print("loginSUccessful...")
    return {"status": "login done"}
    return {"access_token": token, "token_type": "bearer"}'''
    
    
@router.post("/join", response_model=schemas.Token, status_code=201)
async def join(user: schemas.UserJoin):
    if waitlist.find_one({"email": user.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    user_doc = {"email": user.email}
    result = waitlist.insert_one(user_doc)
    user_id = str(result.inserted_id)

    await add_subscriber(user.email)

    token = utils.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


class DummyLogin(BaseModel):
    email: EmailStr
    archetype: str | None = None   # optional field

@router.post("/login")
async def dummy_login(user: DummyLogin):
    # Call MailerLite service to add subscriber
    try:
        await add_subscriber(user.email, user.archetype)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MailerLite failed: {str(e)}")

    return {
        "message": " login successful",
        "email": user.email,
        "archetype": user.archetype
    }



# @router.get("/me", response_model=schemas.UserOut)
# def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Missing bearer token")
#     token = authorization.split(" ", 1)[1]
#     try:
#         payload = utils.decode_token(token)
#         if payload.get("type") != "access":
#             raise HTTPException(status_code=401, detail="Invalid token type")
#         user_id = int(payload["sub"])
#     except Exception:
#         raise HTTPException(status_code=401, detail="Invalid or expired token")

#     user = db.get(models.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user