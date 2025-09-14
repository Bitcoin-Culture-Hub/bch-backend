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
        "fields": {}
        "groups": ["165354171714766481"] # type: ignore
    }

    # If archetype is provided, add it
    if archetype:
        payload["fields"]["archetype"] = archetype

    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.MAILERLITE_API, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
