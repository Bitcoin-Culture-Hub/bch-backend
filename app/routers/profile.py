from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
import boto3
from ..services.auth_service import get_current_user
import os
router = APIRouter(prefix="/profile", tags=["profile"])

dynamodb = boto3.resource("dynamodb",
    region_name=os.environ.get("AWS_REGION", "us-east-2"),
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY")
    )
table = dynamodb.Table("MainAppTable")
s3 = boto3.client("s3")

PROFILE_BUCKET = "my-profile-pictures"


class ProfileUpdate(BaseModel):
    username: str | None = None
    bio: str | None = None
    location: str | None = None
    links: list[str] | None = None


@router.get("/")
def get_profile(current_user=Depends(get_current_user)):
    user_id = current_user["user_id"]  # UUID

    resp = table.get_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"}
    )

    if "Item" not in resp:
        raise HTTPException(404, "Profile not found")

    return resp["Item"]


@router.patch("/")
def update_profile(update: ProfileUpdate, current_user=Depends(get_current_user)):
    print(current_user)
    user_id = current_user["user_id"]
    print('Hi')
    resp = table.get_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"}
    )
    print(resp,'PRINTING')
    if "Item" not in resp:
        print('account not found')
        raise HTTPException(404, "Profile not found")

    profile = resp["Item"]
    print(profile)
    if update.username is not None:
        profile["username"] = update.username

    if update.bio is not None:
        profile["bio"] = update.bio

    if update.location is not None:
        profile["location"] = update.location

    if update.links is not None:
        profile["links"] = update.links

    table.put_item(Item=profile)
    print('done running')
    return {"message": "Profile updated", "profile": profile}


@router.post("/upload-picture")
def upload_picture(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    user_id = current_user["user_id"]

    filename = f"{user_id}/profile.png"

    s3.upload_fileobj(
        file.file,
        PROFILE_BUCKET,
        filename,
        ExtraArgs={"ContentType": file.content_type},
    )

    picture_url = f"https://{PROFILE_BUCKET}.s3.amazonaws.com/{filename}"

    table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        UpdateExpression="SET profile_picture = :u",
        ExpressionAttributeValues={":u": picture_url},
    )

    return {"message": "Upload success", "url": picture_url}
