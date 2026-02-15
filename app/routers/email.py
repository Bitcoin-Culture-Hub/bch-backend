from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
import boto3
from pydantic import BaseModel, EmailStr
import os



router = APIRouter(prefix="/email", tags=["email"])
ses_client = boto3.client("ses", region_name="us-east-2",aws_access_key_id=os.environ["BITCOIN_AWS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["BITCOIN_AWS_SECRET_ACCESS_KEY"])


class JoinOrgEmailRequest(BaseModel):
    org_name: str
    from_email: EmailStr
    sender_name: str
    sender_title: str
    join_link: str
    to_email: EmailStr
    
    
def generate_interview_email(
    candidate_name: str,
    role_title: str,
    company_name: str,
    from_email: str,
    interviewer_name: str,
    interviewer_title: str,
    company_website: str,
    interview_type: str,
    interview_duration: str,
    interview_dates: str,
    scheduling_link: str,
    to_email: str,
) -> str:
    """
    Returns MIME-formatted HTML for the interview email
    """
    return f"""From: {company_name} <{from_email}>
To: {to_email}
Subject: Interview Invitation – {role_title} at {company_name}
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

<!DOCTYPE html>
<html>
  <head>
    <title>Interview Invitation – {company_name}</title>
  </head>
  <body>
    <div style="font-family: Montserrat, Arial, sans-serif; color:#333; font-size:18px;">

      <h1 style="color:#F7931A; font-size:32px;">
        Interview Invitation 🚀
      </h1>

      <p>Hi {candidate_name},</p>

      <p>
        Thank you for your interest in the <strong>{role_title}</strong> role at
        <strong>{company_name}</strong>. We’ve reviewed your application and are excited to move
        forward with the interview process.
      </p>

      <p>
        We’d love the opportunity to learn more about your experience, skills, and interests, and
        to share more about our team, culture, and the impact you could make with us.
      </p>

      <p>
        <strong>Interview details:</strong><br />
        • Format: {interview_type}<br />
        • Duration: {interview_duration}<br />
        • Availability: {interview_dates}
      </p>

      <p>Please use the link below to select a time that works best for you.</p>

      <br />

      <a
        href="{scheduling_link}"
        style="background:#F7931A;color:#ffffff;padding:12px 24px;border-radius:6px;
               text-decoration:none;font-size:18px;display:inline-block;"
      >
        Schedule Your Interview
      </a>

      <br /><br />

      <p>If you have any questions or need accommodations, feel free to reply directly to this email.</p>

      <p>We’re looking forward to speaking with you.</p>

      <p>
        Best regards,<br />
        {interviewer_name}<br />
        {interviewer_title}<br />
        {company_name}<br />
        {company_website}
      </p>

      <br /><br />

      <img
        src="https://i.imgur.com/GtE82qY.png"
        alt="Bitcoin Culture Hub Header"
        style="width:70%;max-width:500px;margin-top:20px;"
      />

    </div>
  </body>
</html>
"""

def generate_join_org_email(
    org_name: str,
    from_email: str,
    sender_name: str,
    sender_title: str,
    join_link: str,
    to_email: str,
) -> str:
    """
    Returns MIME-formatted HTML for a 'Join Our Organization' invitation email
    """
    # get the username of the email address since adding an extra field to the website looks kinda ugly 
    recipient_name = to_email.split("@")[0] 
    
    # get the organization name from the 
    return f"""From: {org_name} <{from_email}>
To: {to_email}
Subject: Welcome to Bitcoin Culture Hub! 🚀
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

<!DOCTYPE html>
<html>
  <head>
    <title>Welcome to {org_name}!</title>
  </head>
  <body>
    <div style="font-family: Montserrat, Arial, sans-serif; color:#333; font-size:18px;">

      <h1 style="color:#F7931A; font-size:32px;">
        You're Invited! 🔥
      </h1>

      <p>Hi {recipient_name},</p>

      <p>
        We’re thrilled to invite you to join <strong>{org_name}</strong>! Our community exists to
        empower creators, builders, and innovators to make an impact and connect with like-minded people.
      </p>

      <p>
        By joining, you’ll gain access to exclusive events, resources, and a network of forward-thinking
        members shaping the future.
      </p>

      <p>
        Click the button below to get started and become part of the {org_name} community.
      </p>

      <br />

      <a
        href="{join_link}"
        style="background:#F7931A;color:#ffffff;padding:12px 24px;border-radius:6px;
               text-decoration:none;font-size:18px;display:inline-block;"
      >
        Join {org_name} Now
      </a>

      <br /><br />

      <p>If you have any questions, feel free to reply directly to this email. We’re here to help!</p>

      <p>Excited to see you onboard!</p>

      <p>
        Best regards,<br />
        {sender_name}<br />
        {sender_title}<br />
        {org_name}<br />
        www.bitcoinculturehub.com
      </p>

      <br /><br />

      <img
        src="https://i.imgur.com/GtE82qY.png"
        alt="{org_name} Header"
        style="width:70%;max-width:500px;margin-top:20px;"
      />

    </div>
  </body>
</html>
"""


@router.post("/send-join-org-email",  response_class=JSONResponse)
def send_join_org_email(
    request:JoinOrgEmailRequest
):
    try:
        raw_email = generate_join_org_email(
            org_name=request.org_name,
            from_email=request.from_email,
            sender_name=request.sender_name,
            sender_title=request.sender_title,
            join_link=request.join_link,
            to_email=request.to_email,
        )
        response = ses_client.send_raw_email(
            RawMessage={"Data": raw_email},
            Source=request.from_email,
            Destinations=[request.to_email],
        )

        return {"success": True, "message_id": response["MessageId"]}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")