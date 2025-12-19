import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from boto3.dynamodb.conditions import Key

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
router = APIRouter(prefix="/org", tags=["organizations"])


# ----------------------------------------------------
# Create Organization
# ----------------------------------------------------
@router.post("/", response_model=OrgResponse)
def create_org(data: OrgCreate, user=Depends(get_current_user)):
    org_id = str(uuid.uuid4())
    submitted = datetime.utcnow().isoformat()

    # Org core item
    item = {
        "PK": f"ORG#{org_id}",
        "SK": "ORG",

        "id": org_id,
        "name": data.name,
        "type": data.type,
        "location": data.location,
        "email": data.email,
        "status": "pending",             
        "submittedAt": submitted,
        "description": data.description,
        "owner_id": user["user_id"],
        
    }

    table.put_item(Item=item)

    table.put_item(Item={
        "PK": f"ORG#{org_id}",
        "SK": f"MEMBER#{user['user_id']}",

        "userId": user["user_id"],
        "role": "owner",
        "joinedAt": submitted,

        "GSI1PK": f"USER#{user['user_id']}",
        "GSI1SK": f"ORG#{org_id}",
    })

    return item

@router.get("/")
def get_all_opportunities():
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq("OPPORTUNITY")
    )
    
    return resp.get("Items", [])

@router.get("/my")
def get_my_organizations(user=Depends(get_current_user)):
    print('HIIIIIIII')
    user_id = user["user_id"]
    
    # Step 1: find orgs the user belongs to
    resp = table.query(
        IndexName="UserOrgsIndex",
        KeyConditionExpression=Key("GSI1PK").eq(f"USER#{user_id}")
    )
    print(resp)
    org_ids = [
        item["GSI1SK"].replace("ORG#", "")
        for item in resp.get("Items", [])
    ]

    orgs = []

    for org_id in org_ids:
        core = table.get_item(
            Key={"PK": f"ORG#{org_id}", "SK": "ORG"}
        )
        if "Item" not in core:
            continue
        org = core["Item"]

        owner_resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"ORG#{org_id}") &
                                   Key("SK").begins_with("OWNER#")
        )

        members = owner_resp.get("Items", [])
        owner = next((m for m in members if m.get("role") == "owner"), None)

        if owner is None:
            owner = {
                "userId": org["owner_id"],
                "role": "owner",
                "joinedAt": org["submittedAt"]
            }

        orgs.append({
            "id": org["id"],
            "name": org["name"],
            "type": org["type"],
            "location": org["location"],
            "email": org["email"],
            "status": org["status"],
            "submittedAt": org["submittedAt"],
            "description": org.get("description"),
            "website": org.get("website"),
            "owner": owner
        })

    return {"organizations": orgs}

@router.get("/{org_id}", response_model=OrgResponse)
def get_organization(org_id: str):
    resp = table.get_item(
        Key={"PK": f"ORG#{org_id}", "SK": "ORG"}
    )

    if "Item" not in resp:
        raise HTTPException(404, "Organization not found")

    return resp["Item"]


# ----------------------------------------------------
# List members
# ----------------------------------------------------
@router.get("/{org_id}/members")
def list_members(org_id: str):
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"ORG#{org_id}") &
                               Key("SK").begins_with("MEMBER#")
    )
    return resp["Items"]


# ----------------------------------------------------
# Add member manually
# ----------------------------------------------------
@router.post("/{org_id}/members/add")
def add_member(org_id: str, data: AddMember):
    item = {
        "PK": f"ORG#{org_id}",
        "SK": f"MEMBER#{data.userId}",

        "userId": data.userId,
        "role": data.role,
        "joinedAt": datetime.utcnow().isoformat(),

        "GSI1PK": f"USER#{data.userId}",
        "GSI1SK": f"ORG#{org_id}",
    }

    table.put_item(Item=item)

    return {"message": "Member added", **item}


