from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional,List
from datetime import datetime

class User(BaseModel):
    email: EmailStr
class UserJoin(BaseModel):
    email:str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    results: Optional[List[Dict[str, Any]]] = None  
  

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RegisterToken(BaseModel):
    access_token: str
    token_type: str
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    email: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    class Config:
        from_attributes = True
        
class BookmarkBase(BaseModel):
    title: str
    user_email: EmailStr
    itemType: str
    tags: Optional[List[str]] = []

class BookmarkCreate(BookmarkBase):
    pass

class BookmarkOut(BaseModel):
    id: str
    title: str
    itemType: str
    tags: List[str]
    user: User
    created_at: datetime

    class Config:
        from_attributes = True