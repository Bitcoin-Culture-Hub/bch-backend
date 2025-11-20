from typing import List
import uuid
import os
from fastapi import APIRouter, Body, HTTPException, Form
import boto3
from botocore.exceptions import ClientError
router = APIRouter(prefix="/jobs", tags=["Jobs"])

dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.environ.get("AWS_REGION", "us-east-2"),
    aws_access_key_id=os.environ.get("BITCOIN_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("BITCOIN_AWS_SECRET_ACCESS_KEY"),
)

TABLE_NAME = os.environ.get("JOBS_TABLE", "opportunities")
table = dynamodb.Table("opportunities")


@router.post("/", response_model=dict)
def create_job(
    title: str = Form(...),
    description: str = Form(...),
    type: str = Form(...),
    postedBy: str = Form(...),
    remote: bool = Form(...),
    postedDate: str = Form(...)
):
    job_id = str(uuid.uuid4())

    item = {
        "jobID": job_id,
        "title": title,
        "description": description,
        "type": type,
        "postedBy": postedBy,
        "remote": remote,
        "postedDate": postedDate,
        "applicants": [] 
    }

    try:
        table.put_item(Item=item)
        return {"ok": True, "jobId": job_id}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[dict])
def list_jobs():
    try:
        response = table.scan()
        return response.get("Items", [])
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{job_id}", response_model=dict)
def get_job(job_id: str):
    try:
        response = table.get_item(Key={"jobID": job_id})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Job not found")
        return response["Item"]
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.patch("/{job_id}/apply", response_model=dict)
def add_applicants(job_id: str, applicants: List[str] = Body(...)):

    try:
        response = table.update_item(
            Key={"jobID": job_id},
            UpdateExpression="SET applicants = list_append(if_not_exists(applicants, :empty), :new)",
            ExpressionAttributeValues={
                ":new": applicants,
                ":empty": [],
            },
            ReturnValues="ALL_NEW"
        )
        return response["Attributes"]
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}/remove", response_model=dict)
def remove_applicant(job_id: str, applicant: str = Form(...)):
    try:
        # Get job first
        job = table.get_item(Key={"jobID": job_id}).get("Item")
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        applicants = job.get("applicants", [])
        if applicant not in applicants:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Remove in Python then overwrite
        applicants.remove(applicant)

        response = table.update_item(
            Key={"jobID": job_id},
            UpdateExpression="SET applicants = :updated",
            ExpressionAttributeValues={":updated": applicants},
            ReturnValues="ALL_NEW"
        )

        return response["Attributes"]

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
