
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Any, Dict, Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    results: Optional[Dict[str, Any]] = None   
    
class BookmarkOut(BaseModel):
    id: Optional[str]
    title: str
    user_email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True