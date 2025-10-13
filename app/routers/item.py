from fastapi import APIRouter, HTTPException, status
from ..db import bookmark_collection
from .. import schemas
from datetime import datetime
from typing import List
from bson import ObjectId

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

@router.post("/", response_model=schemas.BookmarkOut, status_code=status.HTTP_201_CREATED)
async def create_bookmark(bookmark: schemas.BookmarkCreate):
    # Check if the bookmark already exists for the same user and title
    existing = bookmark_collection.find_one({
        "title": bookmark.title,
        "user_email": bookmark.user_email
    })
    if existing:
        raise HTTPException(status_code=409, detail="Bookmark already exists")

    new_bookmark = {
        "title": bookmark.title,
        "user_email": bookmark.user_email,
        "itemType": bookmark.itemType,
        "tags": bookmark.tags or [],
        "created_at": datetime.utcnow()
    }

    result = bookmark_collection.insert_one(new_bookmark)
    new_bookmark["_id"] = str(result.inserted_id)
    print(result)
    return {
        "id": new_bookmark["_id"],
        "title": new_bookmark["title"],
        "itemType": new_bookmark["itemType"],
        "tags": new_bookmark["tags"],
        "user": {"email": new_bookmark["user_email"]},
        "created_at": new_bookmark["created_at"]
    }


@router.get("/{user_email}", response_model=List[schemas.BookmarkOut])
async def get_user_bookmarks(user_email: str):
    bookmarks = list(bookmark_collection.find({"user_email": user_email}))
    return [
        {
            "id": str(b["_id"]),
            "title": b["title"],
            "itemType": b.get("itemType", ""),
            "tags": b.get("tags", []),
            "user": {"email": b["user_email"]},
            "created_at": b["created_at"]
        }
        for b in bookmarks
    ]

# Delete a bookmark by ID
@router.delete("/{bookmark_id}", status_code=200)
async def delete_bookmark(bookmark_id: str):
    result = bookmark_collection.delete_one({"_id": ObjectId(bookmark_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    return {"message": "Bookmark deleted successfully"}
