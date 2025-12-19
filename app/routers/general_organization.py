import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from boto3.dynamodb.conditions import Key,Attr

from ..services.auth_service import get_current_user
from ..models.organization_model import OrgCreate, OrgResponse, AddMember
import boto3
import os

dynamodb = boto3.resource("dynamodb",
    region_name=os.environ.get("AWS_REGION", "us-east-2"),
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY")
    )
table = dynamodb.Table("MainAppTable")
router = APIRouter(prefix="/general/org", tags=["organizations"])




@router.get("/")
def get_all_organization():
    resp = table.scan(
        FilterExpression=
            Key("PK").begins_with("ORG") & Attr("SK").eq("ORG")
    )
    return resp.get("Items", [])