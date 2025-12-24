# app/services/mailer.py
import httpx
from app.config import settings
from app.services.ses_email import send_email_ses

async def add_subscriber(email: str, archetype: str | None = None):
    headers = {
        "Authorization": f"Bearer {settings.MAILERLITE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "email": email,
        "fields": {},
        "groups": ["165354171714766481"]
    }

    # If archetype is provided, add it
    if archetype:
        payload["fields"]["archetype"] = archetype

    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.MAILERLITE_API, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


# ----------------------------------------
# SEND PASSWORD RESET EMAIL (LOCAL TEST MODE)
# ----------------------------------------

async def send_reset_email(email: str, token: str):
    reset_url = f"http://localhost:8080/reset-password/{token}"


    subject = "Reset Your Password"
    
    html_body = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>You requested a password reset.</p>
            <p>Click the link below to reset your password (valid for 30 minutes):</p>
            <a href="{reset_url}">{reset_url}</a>
            <p>If you did not request this, you can ignore this email.</p>
        </body>
    </html>
    """

    return send_email_ses(email, subject, html_body)
