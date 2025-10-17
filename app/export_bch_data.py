from pymongo import MongoClient
import gridfs
import json
import os

SOURCE_URI ="mongodb+srv://chanduswamy06_db_user:XANNKwPmvdR2SF9g@cluster0.btvx9xu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(SOURCE_URI)
db = client["bch"]

# Export Explore data
explore_data = list(db["explore"].find({}, {"_id": 0}))
os.makedirs("exported_data", exist_ok=True)
with open("exported_data/explore.json", "w") as f:
    json.dump(explore_data, f, indent=4)

# Export images from GridFS
fs = gridfs.GridFS(db, collection="images")
for file_doc in db["images.files"].find():
    filename = file_doc["filename"]
    with open(f"exported_data/{filename}", "wb") as f:
        f.write(fs.get(file_doc["_id"]).read())

print("✅ Export complete: data and images saved to /exported_data")
