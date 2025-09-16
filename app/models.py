
from pydantic import BaseModel, EmailStr

from typing import Any, Dict, Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    results: Optional[Dict[str, Any]] = None   