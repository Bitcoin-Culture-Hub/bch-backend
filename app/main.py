from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import  health, users, explore,item,opportunity2,organization2,profile2,auth3,general_organization,events
#from .db import Base, engine
from app.db import db



#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bitcoin Culture Hub API")

origins = [
    "http://localhost:5173",  # for Vite frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# routers
app.include_router(health.router)       # GET /        # /auth/*
app.include_router(users.router)
app.include_router(explore.router)
app.include_router(organization2.router)
app.include_router(opportunity2.router)
app.include_router(profile2.router)
app.include_router(auth3.router)
app.include_router(general_organization.router)
app.include_router(events.router)
@app.get("/debug/db")
def debug_db():
    try:
        return {
            "db_name": db.name,
            "collections": db.list_collection_names()
        }
    except Exception as e:
        return {"error": str(e)}
app.include_router(item.router)
