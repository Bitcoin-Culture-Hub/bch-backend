from pydantic import BaseModel
from typing import List, Optional

class OpportunityCreate(BaseModel):
    title: str
    type: str
    description:str
    location:str
    categories:list[str]
    timeCommitment:str

class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    categories:list[str]
    timeCommitment:str
class ApplyRequest(BaseModel):
    org_id: str
    email: str
    username: str
    location: str
    avatar: str
    opp_id:str