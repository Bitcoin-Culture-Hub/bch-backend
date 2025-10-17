from pymongo import MongoClient
import gridfs
import json
import os

DEST_URI = "mongodb+srv://chandu_migrate:8a3sdkAONgWyOrHO@cluster0.1fvin.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
print("🔌 Connecting to MongoDB...")
client = MongoClient(DEST_URI)
db = client["BitcoinCultureHub"]
print("✅ Connected to destination DB:", db.name)
# Import Explore data
try:
    with open("exported_data/explore.json") as f:
        explore_data = json.load(f)
    if explore_data:
        db["explore"].insert_many(explore_data)
        print(f"✅ Imported {len(explore_data)} explore records")
except Exception as e:
    print("❌ Error while inserting Explore data:", e)
# Upload images to GridFS

try:
    fs = gridfs.GridFS(db, collection="images")
    for filename in os.listdir("exported_data"):
        if filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
            with open(f"exported_data/{filename}", "rb") as f:
                fs.put(f.read(), filename=filename)
    print("✅ Uploaded all images to GridFS")
except Exception as e:
    print("❌ Error uploading images:", e)
