from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional,List


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