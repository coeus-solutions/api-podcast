from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import auth, podcasts
from app.config import settings

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Podcast Management API",
    description="API for managing podcasts, transcriptions, and audio clips",
    version="1.0.0",
    openapi_tags=[
        {"name": "Authentication", "description": "Operations with user authentication"},
        {"name": "Podcasts", "description": "Operations with podcasts and clips"},
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(podcasts.router, prefix="/api/v1/podcasts", tags=["Podcasts"])

@app.get("/")
async def root():
    return {"message": "Welcome to Podcast Management API"} 