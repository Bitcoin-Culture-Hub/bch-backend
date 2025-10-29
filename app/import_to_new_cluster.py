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
with open("explore_data.json") as f:
    explore_data = json.load(f)
    for entry in explore_data:
        entry["image_url"] = entry["image_url"].split("/")[-1]
        print(entry)
        print(entry["image_url"])
    if explore_data:
        print(explore_data)
        db["explore2"].insert_many(explore_data)
        print(f"✅ Imported {len(explore_data)} explore records")

# Upload images to GridFS

