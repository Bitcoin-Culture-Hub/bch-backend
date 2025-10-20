import gridfs 
from .config import settings
from pymongo import MongoClient

client = MongoClient(settings.MONGO_URI)

# Specify database and collection
db = client["BitcoinCultureHub"]
collection = db["users"]
explore = db["explore"]
waitlist = db["waitlist"]
fs = gridfs.GridFS(db, collection="images")
bookmark_collection = db["bookmarks"]
# engine = create_engine(settings.DATABASE_URL)

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
