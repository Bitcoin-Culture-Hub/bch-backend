from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()



class Settings(BaseModel):
    print(os.getenv("MONGO_URI"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["*"]
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    MAILERLITE_API: str = "https://connect.mailerlite.com/api/subscribers"
    MAILERLITE_TOKEN: str = os.getenv("MAILERLITE_TOKEN")
    MONGO_URI: str = os.getenv("MONGO_URI")
    # ✅ SES Email Config
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str | None = os.getenv("AWS_REGION")
    SES_SENDER_EMAIL: str | None = os.getenv("SES_SENDER_EMAIL")
settings = Settings()