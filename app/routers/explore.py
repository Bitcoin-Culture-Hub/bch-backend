import io
import json
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from pymongo import MongoClient
from bson import ObjectId
import gridfs
import boto3, uuid
from motor.motor_asyncio import AsyncIOMotorClient
from app.redis_client import redis_client

router = APIRouter(prefix="/explore", tags=["Explore"])

# Mongo setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client["BitcoinCultureHub"]
col = db["explore2"]
fs = gridfs.GridFS(db, collection="images")
BUCKET_NAME = "bitcoin-culture-hub-content-pictures"

# Cache configuration
CACHE_TTL = 3600  # 1 hr
LIST_CACHE_KEY = "explore:list"
ITEM_CACHE_KEY_PREFIX = "explore:item"
PRESIGNED_URL_CACHE_KEY_PREFIX = "explore:presigned_url"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name="us-east-2"
)


def _get_cache_key_for_item(item_id: str) -> str:
    """Generate cache key for a single item"""
    return f"{ITEM_CACHE_KEY_PREFIX}:{item_id}"


def _get_cache_key_for_presigned_url(image_key: str) -> str:
    """Generate cache key for presigned URL"""
    return f"{PRESIGNED_URL_CACHE_KEY_PREFIX}:{image_key}"


def _get_presigned_url(image_key: str) -> str:
    """
    Get presigned URL from cache or generate new one and cache it.
    """
    cache_key = _get_cache_key_for_presigned_url(image_key)
    
    # Try to get from cache
    cached_url = redis_client.get(cache_key)
    if cached_url:
        return cached_url
    
    # Generate new presigned URL
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": image_key},
        ExpiresIn=CACHE_TTL
    )
    
    # Cache it (with slightly shorter TTL than expiry to refresh before expiry)
    redis_client.setex(cache_key, CACHE_TTL - 300, url)
    return url


def _invalidate_cache(item_id: str = None, category: str = None):
    """Invalidate relevant cache entries"""
    # Invalidate list cache
    redis_client.delete(LIST_CACHE_KEY)
    
    # Invalidate category-specific cache if provided
    if category:
        category_key = f"{LIST_CACHE_KEY}:category:{category.lower().strip()}"
        redis_client.delete(category_key)
    
    # Invalidate specific item cache
    if item_id:
        item_cache_key = _get_cache_key_for_item(item_id)
        redis_client.delete(item_cache_key)


@router.get("/", response_model=list[dict])
def list_items(category: str | None = Query(default=None)):
    """
    Return all explore items, optionally filtered by category.
    Caches full list and presigned URLs in Redis.
    """
    
    # Create cache key based on category
    if category:
        cleaned = category.strip().rstrip(",").lower()
        cache_key = f"{LIST_CACHE_KEY}:category:{cleaned}"
    else:
        cache_key = LIST_CACHE_KEY
    
    # Try to get from cache
    cached_items = redis_client.get(cache_key)
    if cached_items:
        print(f"✅ Cache hit for {cache_key}")
        return json.loads(cached_items)
    
    # Query database
    q = {}
    if category:
        cleaned = category.strip().rstrip(",").lower()
        q = {"category": {"$regex": f"^{cleaned}", "$options": "i"}}
    
    items = list(col.find(q, {"_id": 0}))
    
    # Add presigned URLs for each item
    for item in items:
        if item.get("image_url"):
            item["image_url"] = _get_presigned_url(item["image_url"])
    
    # Cache the result
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(items))
    
    print(f"[Explore] Returning {len(items)} items (filter={category})")
    return items


@router.get("/{item_id}", response_model=dict)
def get_item(item_id: str):
    """
    Get single item by ID with caching.
    """
    cache_key = _get_cache_key_for_item(item_id)
    
    # Try cache first
    cached_item = redis_client.get(cache_key)
    if cached_item:
        print(f"✅ Cache hit for item {item_id}")
        return json.loads(cached_item)
    
    # Query database
    item = (
        col.find_one({"id": item_id}, {"_id": 0})
        or col.find_one({"realId": item_id}, {"_id": 0})
    )
    
    if not item:
        raise HTTPException(404, "Item not found")
    
    # Add presigned URL if image exists
    if item.get("image_url"):
        item["image_url"] = _get_presigned_url(item["image_url"])
    
    # Cache the item
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(item))
    
    return item


@router.put("/accept-by-title/{title}", response_model=dict)
def accept_item_by_title(title: str):
    """
    Update item acceptance status and invalidate cache.
    """
    result = col.update_one(
        {"title": title},
        {"$set": {"accepted": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Get updated document
    item = col.find_one({"title": title}, {"_id": 0})
    
    # Invalidate caches
    if item and item.get("id"):
        _invalidate_cache(item_id=item["id"], category=item.get("category"))
    
    # Add presigned URL if image exists
    if item and item.get("image_url"):
        item["image_url"] = _get_presigned_url(item["image_url"])
    
    return item


@router.delete("/delete-by-title/{title}", response_model=dict)
def delete_item_by_title(title: str):
    """
    Delete item and invalidate cache.
    """
    found_item = col.find_one({"title": title})
    
    if not found_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    image_title = found_item.get("image_url")
    item_id = found_item.get("id")
    category = found_item.get("category")
    
    # Delete from database
    result = col.delete_one({"title": title})
    
    # Delete from S3
    if image_title:
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=image_title,
        )
        # Invalidate presigned URL cache
        redis_client.delete(_get_cache_key_for_presigned_url(image_title))
    
    # Invalidate item and list caches
    if item_id:
        _invalidate_cache(item_id=item_id, category=category)
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"ok": True, "title": title, "deleted_count": result.deleted_count}


@router.get("/image/{image_id}")
def serve_image(image_id: str):
    """
    Serve image files from MongoDB GridFS using their ObjectId.
    Note: GridFS images are separate from S3-cached items.
    """
    try:
        oid = ObjectId(image_id)
        file = fs.get(oid)
        
        content_type = getattr(file, "content_type", None) or "image/png"
        
        headers = {
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="{file.filename}"'
        }
        
        return Response(content=file.read(), media_type=content_type, headers=headers)
    
    except gridfs.NoFile:
        raise HTTPException(status_code=404, detail="Image not found in GridFS")
    except Exception as e:
        print(f"Image fetch error: {e}")
        raise HTTPException(status_code=404, detail=f"Image not found or invalid ID: {e}")


@router.post("/", response_model=dict)
async def create_item(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    type: str | None = Form(None),
    tags: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    """
    Create new item and invalidate list cache.
    """
    image_id = uuid.uuid4()
    
    if file:
        content = await file.read()
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file.filename,
            Body=content,
            ContentType=file.content_type,
        )
    
    doc: dict = {
        "id": "-".join(title.lower().split()),
        "title": title,
        "description": description,
        "category": category,
        "type": type,
        "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
        "image_id": str(image_id) if image_id else None,
        "image_url": f"{file.filename}" if file else None,
        "accepted": False
    }
    
    col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
    
    # Invalidate list cache since new item was added
    _invalidate_cache(category=category)
    
    return {"ok": True, "id": doc["id"], "image_id": doc["image_id"]}