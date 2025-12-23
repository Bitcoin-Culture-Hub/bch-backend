import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from boto3.dynamodb.conditions import Key
import boto3
import os

from ..services.auth_service import get_current_user
from ..models.opportunity_model import OpportunityCreate, OpportunityUpdate,ApplyRequest

# DynamoDB Setup
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.environ.get("AWS_REGION", "us-east-2"),
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY")
)

table = dynamodb.Table("MainAppTable")

router = APIRouter(
    prefix="/org/{org_id}/opportunities",
    tags=["opportunities"]
)

# -------------------------
#   Helper Functions
# -------------------------

def ensure_member(org_id: str, user_id: str):
    """Verify the user is part of the organization."""
    resp = table.get_item(
        Key={
            "PK": f"ORG#{org_id}",
            "SK": f"MEMBER#{user_id}"
        }
    )

    if "Item" not in resp:
        raise HTTPException(403, "You are not a member of this organization.")


# -------------------------
#   Opportunity Endpoints
# -------------------------

@router.post("/")
def create_opportunity(org_id: str, data: OpportunityCreate, user=Depends(get_current_user)):
    print(user)
    user_id = user["user_id"]
    ensure_member(org_id, user_id)
    
    opp_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    item = {
        "PK": f"ORG#{org_id}",
        "SK": f"OPP#{opp_id}",

        "id": opp_id,
        "title": data.title,
        "type": data.type,
        "description": data.description,
        "location":data.location,
        "createdAt": now,
        "createdBy": user_id,
        "timeCommitment":data.timeCommitment,
        "categories":data.categories,
        "GSI1PK":"OPPORTUNITY"
    }

    table.put_item(Item=item)
    return item

@router.get("/")
def list_opportunities(org_id: str):
    resp = table.query(
        IndexName="OrganizationSearch",
        KeyConditionExpression= Key("PK").eq(f"ORG#{org_id}") & Key("GSI1PK").eq(f"OPPORTUNITY")
    )
    print(resp)
    return resp["Items"]

@router.get("/{opp_id}")
def get_opportunity(org_id: str, opp_id: str):
    resp = table.get_item(
        Key={
            "PK": f"ORG#{org_id}",
            "SK": f"OPP#{opp_id}"
        }
    )

    if "Item" not in resp:
        raise HTTPException(404, "Opportunity not found")

    return resp["Item"]





@router.patch("/{opp_id}")
def update_opportunity(org_id: str, opp_id: str, data: OpportunityUpdate, user=Depends(get_current_user)):
    ensure_member(org_id, user["user_id"])

    key = {"PK": f"ORG#{org_id}", "SK": f"OPP#{opp_id}"}
    resp = table.get_item(Key=key)

    if "Item" not in resp:
        raise HTTPException(404, "Opportunity not found")

    opp = resp["Item"]

    for field, value in data.dict(exclude_unset=True).items():
        opp[field] = value

    table.put_item(Item=opp)
    return opp


@router.delete("/{opp_id}")
def delete_opportunity(org_id: str, opp_id: str, user=Depends(get_current_user)):
    ensure_member(org_id, user["user_id"])

    table.delete_item(
        Key={
            "PK": f"ORG#{org_id}",
            "SK": f"OPP#{opp_id}"
        }
    )

    return {"message": "Opportunity deleted"}


# -------------------------
#   Applicant Endpoints
# -------------------------

@router.post("/{opp_id}/apply")
def apply(data:ApplyRequest,user=Depends(get_current_user)):
    user_id = user["user_id"]
    apply_id = str(uuid.uuid4())
    # Check if already applied
    resp = table.get_item(
        Key={
            "PK": f"ORG#{data.org_id}",
            "SK": f"OPP#{data.opp_id}#APPLICANT#{user_id}"
        }
    )

    if "Item" in resp:
        raise HTTPException(400, "Already applied")

    item = {
        "PK": f"ORG#{data.org_id}",
        "SK": f"OPP#{data.opp_id}#APPLICANT#{user_id}",
        "id":apply_id,
        "userId": user_id,
        "opportunityId": data.opp_id,
        "appliedAt": datetime.utcnow().isoformat(),
        "status": "new",
        "email":data.email ,
        "username":data.username,
        "location":data.location,
        "avatar":data.avatar
        }

    table.put_item(Item=item)
    return {"message": "Application submitted", **item}


@router.get("/{opp_id}/applicants")
def list_applicants(org_id: str, opp_id: str, user=Depends(get_current_user)):
    ensure_member(org_id, user["user_id"])

    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"ORG#{org_id}") &
                               Key("SK").begins_with(f"OPP#{opp_id}#APPLICANT#")
    )

    return resp["Items"]
