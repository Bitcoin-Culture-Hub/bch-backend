import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from pymongo import MongoClient
from bson import ObjectId
import gridfs

router = APIRouter(prefix="/explore", tags=["Explore"])

# Mongo setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client["BitcoinCultureHub"]
col = db["explore"]
fs = gridfs.GridFS(db, collection="images")


@router.get("/", response_model=list[dict])
def list_items(category: str | None = Query(default=None)):
    """
    Return all explore items, optionally filtered by category,
    and attach a proper MongoDB GridFS image URL.
    """
    base_url = "https://bch-backend-7vjs.onrender.com"  # change when deploying
   # base_url = os.getenv("BASE_URL", "http://localhost:8000")

    q = {}

    if category:
        cleaned = category.strip().rstrip(",").lower()
        q = {"category": {"$regex": f"^{cleaned}", "$options": "i"}}

    items = list(col.find(q, {"_id": 0}))

    for item in items:
        image_id = item.get("image_id")
        if image_id:
            item["image_url"] = f"{base_url}/explore/image/{image_id}"

    print(f"[Explore] Returning {len(items)} items (filter={category})")
    return items



# ✅ Get single item by ID
@router.get("/{item_id}", response_model=dict)
def get_item(item_id: str):
    item = (
        col.find_one({"id": item_id}, {"_id": 0})
        or col.find_one({"realId": item_id}, {"_id": 0})
    )
    if not item:
        raise HTTPException(404, "Item not found")
    return item

@router.put("/accept-by-title/{title}", response_model=dict)
def accept_item_by_title(title: str):
    # Update the first document matching the title
    result = col.update_one(
        {"title": title},
        {"$set": {"accepted": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    # Return the updated document
    item = col.find_one({"title": title}, {"_id": 0})
    return item
@router.delete("/delete-by-title/{title}", response_model=dict)
def delete_item_by_title(title: str):
    """
    Delete the first document in the collection matching the given title.
    """
    result = col.delete_one({"title": title})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"ok": True, "title": title, "deleted_count": result.deleted_count}

@router.get("/image/{image_id}")
def serve_image(image_id: str):
    """
    Serve image files from MongoDB GridFS using their ObjectId.
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
    print('end point getting hit')
    image_id = None
    if file:
        blob = await file.read()
        image_id = fs.put(blob, filename=file.filename, contentType=file.content_type)

    doc: dict = {
        "id": "-".join(title.lower().split()),
        "title": title,
        "description": description,
        "category": category,
        "type": type,
        "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
        "image_id": str(image_id) if image_id else None,
        "image_url": f"/explore/image/{image_id}" if image_id else None,
        "accepted":False
    }
    print(doc)
    col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
    return {"ok": True, "id": doc["id"], "image_id": doc["image_id"]}
