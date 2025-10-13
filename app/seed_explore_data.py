import os
import json
import gridfs
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["bch"]
fs = gridfs.GridFS(db)
col = db["explore"]

print("✅ Connected to MongoDB")

# Path to your explore data JSON
DATA_FILE = os.path.join(os.path.dirname(__file__), "explore_data.json")

print("🚀 Starting Explore data seeding...")
# Read explore data
with open(DATA_FILE, "r") as f:
    explore_data = json.load(f)

# Optional: clear old data
col.delete_many({})
print("🧹 Cleared existing explore collection")

# Insert new data
for item in explore_data:
    image_path = item.get("image_url")
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            image_id = fs.put(img_file, filename=os.path.basename(image_path))
            item["image_id"] = str(image_id)
            item["image_url"] = f"/explore/image/{image_id}"  # you can adjust route
    else:
        print(f"⚠️ Image not found for: {item.get('title', 'Unknown')}")
    col.insert_one(item)
print("✅ Finished seeding!")
print(f"✅ Inserted {len(explore_data)} documents into MongoDB.")
