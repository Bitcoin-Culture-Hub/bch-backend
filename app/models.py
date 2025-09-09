
from pydantic import BaseModel, EmailStr

from pydantic import BaseModel, EmailStr

class User(BaseModel):
    username: str
    email: EmailStr
    password: str