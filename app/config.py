from pydantic_settings import BaseSettings
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Cloudinary Settings
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET")
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL")

    class Config:
        env_file = ".env"

# Constants
MAX_FILE_SIZE: int = 104857600  # 100MB
ALLOWED_AUDIO_TYPES: List[str] = ["audio/mpeg", "audio/mp3"]
CLOUDINARY_FOLDER: str = "podcast_clips"

settings = Settings() 