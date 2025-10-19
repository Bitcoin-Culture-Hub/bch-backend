import os
import json
import gridfs
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "explore_data.json")
IMAGES_DIR = os.path.abspath(os.path.join(BASE_DIR, "public/database_images"))

# --- MongoDB setup ---
client = MongoClient(os.getenv("MONGO_URI"))
db = client["BitcoinCultureHub"]
col = db["explore"]
fs = gridfs.GridFS(db, collection="images")

print("✅ Connected to MongoDB")
print("📂 Image directory:", IMAGES_DIR)
print("📄 JSON data file:", DATA_FILE)

# --- Load JSON data ---
with open(DATA_FILE, "r", encoding="utf-8") as f:
    explore_data = json.load(f)

# --- Upload each image in JSON ---
for item in explore_data:
    image_path = item.get("image_url")
    if not image_path:
        print(f"⚠️ No image URL for: {item.get('title', 'Unknown')}")
        continue

    image_name = os.path.basename(image_path).lstrip("/")
    found_path = None

    # Look for the file anywhere under IMAGES_DIR
    for root, _, files in os.walk(IMAGES_DIR):
        if image_name in files:
            found_path = os.path.join(root, image_name)
            break

    if not found_path:
        print(f"⚠️ Not found: {image_name} for {item.get('title', 'Unknown')}")
        continue

    # --- Upload to GridFS properly (stream, not read) ---
    with open(found_path, "rb") as img_file:
        image_id = fs.put(
            img_file,
            filename=image_name,
            contentType="image/png"
        )

    # --- Update or insert explore document ---
    col.update_one(
        {"title": item["title"]},
        {
            "$set": {
                "image_id": str(image_id),
                "image_url": f"/explore/image/{image_id}",
            }
        },
        upsert=True,
    )

    print(f"✅ Uploaded: {item['title']} → {image_name} ({image_id})")

print("\n🎉 All images uploaded and database updated!")

# --- Verification Summary ---
print("\n📊 Checking GridFS consistency...")
num_files = db.images.files.count_documents({})
num_chunks = db.images.chunks.count_documents({})
print(f"   Files in images.files:  {num_files}")
print(f"   Chunks in images.chunks: {num_chunks}")

# --- Optional sanity check: ensure every file has chunks ---
missing_chunks = list(db.images.files.aggregate([
    {"$lookup": {
        "from": "images.chunks",
        "localField": "_id",
        "foreignField": "files_id",
        "as": "chunks"
    }},
    {"$match": {"chunks": {"$size": 0}}},
    {"$project": {"filename": 1}}
]))

if missing_chunks:
    print("\n⚠️ Files missing chunks:")
    for m in missing_chunks:
        print("  -", m["filename"])
else:
    print("✅ All files have chunks properly stored!")
