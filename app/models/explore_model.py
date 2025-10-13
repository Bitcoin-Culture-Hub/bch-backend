from pydantic import BaseModel, Field
from typing import List, Optional

class ExploreItemIn(BaseModel):
    id: Optional[str] = None
    realId: Optional[str] = None
    title: str
    description: str
    category: str  # 'Artifacts' | 'Creators' | 'Memes' | 'Communities' | 'Events'
    summary: Optional[str] = None
    tags: List[str] = []
    bio: Optional[str] = None
    genesis: Optional[str] = None
    development: Optional[str] = None
    legacy: Optional[str] = None
    content: Optional[str] = None
    external_url: Optional[str] = None
    logo_url: Optional[str] = None
    type: Optional[str] = None   # 'artifact' | 'creator' | 'community' | 'event' | 'meme'
    image_id: Optional[str] = None  # GridFS id string

class ExploreItemOut(ExploreItemIn):
    pass
