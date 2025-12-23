# from pydantic import BaseModel, Field
# from typing import List, Optional,Literal



# class OrgCreate(BaseModel):
#     name: str
#     type: str
#     location: str
#     email: str
#     description: Optional[str] = None
#     website: Optional[str] = None


# class OrgResponse(BaseModel):
#     id: str
#     name: str
#     type: str
#     location: str
#     email: str
#     status: str
#     submittedAt: str
#     description: Optional[str] = None
#     website: Optional[str] = None


# class AddMember(BaseModel):
#     userId: str
#     role: str = "member"



# class OpportunityCreate(BaseModel):
#     title: str
#     type: Literal["Job", "Collaboration", "Grant", "Volunteer"]
#     description: str


# class OpportunityResponse(BaseModel):
#     id: str
#     title: str
#     type: str
#     description: str
#     postedAt: str
    

