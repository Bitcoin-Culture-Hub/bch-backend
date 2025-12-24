# app/services/mailer.py
import httpx
from app.config import settings


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


    print("\n===============================")
    print("📩 PASSWORD RESET EMAIL (LOCAL)")
    print("===============================")
    print(f"To: {email}")
    print(f"Reset Link: {reset_url}")
    print("===============================\n")

    return True
