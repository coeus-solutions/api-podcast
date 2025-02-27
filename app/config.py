from pydantic_settings import BaseSettings
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30000
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Stripe Settings
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_SUCCESS_URL: str = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/payment/success")
    STRIPE_CANCEL_URL: str = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/payment/cancel")
    
    # Token Pricing (in cents)
    TOKEN_PRICE_PER_1000: int = 100  # $1 per 1000 tokens
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Using service role key for storage operations
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY")  # Keep anon key for client-side operations
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "videos")

    # Render Settings
    RENDER_API_KEY: str = os.getenv("RENDER_API_KEY")
    
    # Mailjet Settings
    MAILJET_API_KEY: str = os.getenv("MAILJET_API_KEY")
    MAILJET_SECRET_KEY: str = os.getenv("MAILJET_SECRET_KEY")
    MAILJET_SENDER_EMAIL: str = os.getenv("MAILJET_SENDER_EMAIL", "your-verified-sender@email.com")
    MAILJET_SENDER_NAME: str = os.getenv("MAILJET_SENDER_NAME", "Podcast App")

    class Config:
        env_file = ".env"

# Constants
MAX_FILE_SIZE: int = 104857600 # 100MB
ALLOWED_MEDIA_TYPES: List[str] = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]

settings = Settings() 