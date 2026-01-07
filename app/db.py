import gridfs
from pymongo import MongoClient
# from your_module import get_session, engine
from .services.auth_service import get_current_user
import os
from sqlmodel import SQLModel
from .config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
import os
# --------------------------
# MongoDB setup
# --------------------------
client = MongoClient(settings.MONGO_URI)

# Specify database and collections
db = client["BitcoinCultureHub"]
collection = db["users"]
explore = db["explore"]
waitlist = db["waitlist"]
fs = gridfs.GridFS(db, collection="images")
bookmark_collection = db["bookmarks"]

# --------------------------
# MySQL / SQLModel setup
# --------------------------


# --------------------------
# Optional / commented-out legacy code
# --------------------------
# engine = create_engine(settings.DATABASE_URL)
# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
# Base = declarative_base()
#
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


DATABASE_URL = os.environ["DEPLOYED_DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,   
    expire_on_commit=False
)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session