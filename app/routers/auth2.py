from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key
from ..services.password import hash_password, verify_password
from ..services.auth_service import create_access_token
import os
from fastapi import Response

router = APIRouter(prefix="/authorize", tags=["auth"])

dynamodb = boto3.resource("dynamodb",
    region_name=os.environ.get("AWS_REGION", "us-east-2"),
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY")
    )
table = dynamodb.Table("MainAppTable")


# ---------------------------------------------------
# Request Models
# ---------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------
# SIGNUP
# ---------------------------------------------------
@router.post("/signup", status_code=201)
async def signup(user: UserCreate):
    print(user)
    email_lookup = table.query(
        IndexName="EmailIndex",
        KeyConditionExpression=Key("email").eq(user.email)
    )

    if email_lookup["Items"]:
        raise HTTPException(409, "Email already registered")

    username_lookup = table.query(
        IndexName = "UsernameIndex",
        KeyConditionExpression = Key("username").eq(user.username)
    )

    user_id = str(uuid.uuid4())

    hashed = hash_password(user.password)

    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": "AUTH",

            "email": user.email,
            "hashed_password": hashed,
            "created_at": datetime.utcnow().isoformat(),

            "GSI1PK": f"EMAIL#{user.email}",
            "GSI1SK": f"USER#{user_id}",
        }
    )

    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "username": user.username,
            "bio": "",
            "location": "",
            "links": [],
            "profile_picture": None
        }
    )

    token = create_access_token({"sub": user_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id
    }


@router.post("/login")
async def login(user: UserLogin):
    resp = table.query(
        IndexName="LoginIndex",
        KeyConditionExpression=Key("email").eq(user.email) & Key("SK").eq("AUTH")
    )
    if not resp.get("Items"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    auth_item = resp["Items"][0]
    # get user attributes (reason for this is less fetching for multiple attributes)
    user_id = auth_item["PK"].replace("USER#", "")
    pk = auth_item['PK']
    print(user_id, 'user id')
    profile_query = table.query(
        KeyConditionExpression=Key("PK").eq(pk) & Key("SK").eq("PROFILE")
    )
    print(profile_query)
    profile_information = profile_query["Items"][0]
    links = profile_information["links"]
    location = profile_information["location"]
    profile_picture = profile_information["profile_picture"]
    if not profile_picture:
        profile_picture = "https://avatars.githubusercontent.com/u/0?v=4"
    username = profile_information["username"]
    bio = profile_information["bio"]
    print(profile_information)
    if not verify_password(user.password, auth_item["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user_id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "email":user.email,
        "links":links,
        "location":location,
        "profile_picture":profile_picture,
        "username":username,
        "bio": bio
    }