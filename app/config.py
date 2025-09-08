from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()



class Settings(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    MAILERLITE_API: str = "https://connect.mailerlite.com/api/subscribers"
    MAILERLITE_TOKEN: str = os.getenv("MAILERLITE_TOKEN")

settings = Settings()