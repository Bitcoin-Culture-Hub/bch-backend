from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, health, users  
#from .db import Base, engine



#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bitcoin Culture Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(health.router)       # GET /
app.include_router(auth.router)         # /auth/*
app.include_router(users.router)