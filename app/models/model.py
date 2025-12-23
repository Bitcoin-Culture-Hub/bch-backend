from sqlmodel import Relationship, SQLModel, Field
from datetime import datetime
from typing import Optional
from sqlalchemy import UniqueConstraint
import uuid


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Profile(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    username: str = Field(unique=True, index=True)
    bio: Optional[str] = ""
    location: Optional[str] = ""
    profile_picture: Optional[str] = None


class ProfileLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="profile.user_id")
    url: str


class Organization(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    type: Optional[str]
    location: Optional[str]
    email: Optional[str]
    description: Optional[str]
    status: str = "pending"
    owner_id: str = Field(foreign_key="user.id")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class OrganizationMember(SQLModel, table=True):
    org_id: str = Field(foreign_key="organization.id", primary_key=True)
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    role: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class Opportunity(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organization.id", index=True)
    title: str
    type: Optional[str]
    description: Optional[str]
    location: Optional[str]
    time_commitment: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(foreign_key="user.id")

    class Config:
        orm_mode = True


class OpportunityCategory(SQLModel, table=True):
    opportunity_id: str = Field(foreign_key="opportunity.id", primary_key=True)
    category: str = Field(primary_key=True)


class Application(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("opportunity_id", "user_id"),)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    opportunity_id: str = Field(foreign_key="opportunity.id", index=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    email: Optional[str]
    username: Optional[str]
    location: Optional[str]
    avatar: Optional[str]
    status:Optional[str]


class OpportunityRead(SQLModel):
    id: str
    org_id: str
    title: str
    type: Optional[str]
    description: Optional[str]
    location: Optional[str]
    time_commitment: Optional[str]
    created_at: datetime
    created_by: str
    org_name:Optional[str]
    class Config:
        orm_mode = True