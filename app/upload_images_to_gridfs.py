import os
import json
import gridfs
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
db = client["bch"]
col = db["explore"]
fs = gridfs.GridFS(db, collection="images")

print("✅ Connected to MongoDB")
print("📂 Image directory:", IMAGES_DIR)
print("📄 JSON data file:", DATA_FILE)

# --- Load Explore JSON data ---
with open(DATA_FILE, "r") as f:
    explore_data = json.load(f)

# --- Upload each image referenced in JSON ---
for item in explore_data:
    image_path = item.get("image_url")
    if not image_path:
        continue

    # Remove leading slash if present
    image_path = image_path.lstrip("/")

    # Find the actual image file (could be nested)
    found_path = None
    for root, _, files in os.walk(IMAGES_DIR):
        for f_name in files:
            if f_name == os.path.basename(image_path):
                found_path = os.path.join(root, f_name)
                break
        if found_path:
            break

    if not found_path:
        print(f"⚠️ Not found for: {item['title']} → {image_path}")
        continue

    # Upload to GridFS
    with open(found_path, "rb") as img_file:
        image_id = fs.put(
            img_file.read(),
            filename=os.path.basename(found_path),
            contentType="image/png"
        )

    # Update explore document with new image reference
    col.update_one(
        {"title": item["title"]},
        {
            "$set": {
                "image_id": str(image_id),
                "image_url": f"/explore/image/{image_id}"
            }
        },
        upsert=True
    )

    print(f"✅ Uploaded: {item['title']} → {os.path.basename(found_path)} ({image_id})")

print("\n🎉 All JSON-linked images uploaded successfully and MongoDB updated!")
