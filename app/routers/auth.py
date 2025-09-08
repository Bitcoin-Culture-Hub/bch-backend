from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import EmailStr, BaseModel
from ..db import get_db
from .. import models, schemas, utils
from ..services.mailer import add_subscriber

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=schemas.Token, status_code=201)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # email unique
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    # username unique
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")

    u = models.User(
        username=user.username,
        email=user.email,
        hashed_password=utils.hash_password(user.password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    
    await add_subscriber(u.email)

    token = utils.create_access_token({"sub": str(u.id)})
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
    
# ------------------------------
# DUMMY LOGIN (MailerLite only)
# ------------------------------
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.services.mailer import add_subscriber

router = APIRouter()

# Request body
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



@router.get("/me", response_model=schemas.UserOut)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = utils.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user