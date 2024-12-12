from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import aiofiles

from app.database import get_db
from app.models.models import User, Podcast, KeyPoint
from app.schemas.schemas import PodcastCreate, Podcast as PodcastSchema, KeyPoint as KeyPointSchema
from app.routers.auth import get_current_user
from app.services.openai_service import transcribe_audio, extract_key_points
from app.services.cloudinary_service import upload_audio, create_audio_clip, delete_audio
from app.config import settings, ALLOWED_AUDIO_TYPES, MAX_FILE_SIZE

router = APIRouter()

# Create upload directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/", response_model=PodcastSchema, description="Upload a new podcast")
async def create_podcast(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    # Validate file type
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_AUDIO_TYPES)}"
        )

    try:
        # Read file contents
        file_contents = await file.read()
        if len(file_contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE/1024/1024}MB"
            )
        
        # Upload to Cloudinary
        cloudinary_url = await upload_audio(file_contents)
        
        # Create podcast record
        db_podcast = Podcast(
            title=title,
            file_path=cloudinary_url,
            owner_id=current_user.id
        )
        db.add(db_podcast)
        db.commit()
        db.refresh(db_podcast)
        
        # Start transcription and key point extraction
        transcript = await transcribe_audio(cloudinary_url)
        key_points = await extract_key_points(transcript)
        
        # Update podcast with transcript
        db_podcast.transcript = transcript
        db.commit()
        
        # Create key points
        for point in key_points:
            clip_url = await create_audio_clip(cloudinary_url, point["start_time"], point["end_time"])
            db_key_point = KeyPoint(
                content=point["content"],
                start_time=point["start_time"],
                end_time=point["end_time"],
                file_path=clip_url,
                podcast_id=db_podcast.id
            )
            db.add(db_key_point)
        
        db.commit()
        db.refresh(db_podcast)
        return db_podcast
        
    except Exception as e:
        # If there's an error, try to clean up any created resources
        if 'db_podcast' in locals():
            db.delete(db_podcast)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=List[PodcastSchema], description="List all podcasts")
async def list_podcasts(
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    podcasts = db.query(Podcast).filter(Podcast.owner_id == current_user.id).all()
    return podcasts

@router.get("/{podcast_id}", response_model=PodcastSchema, description="Get podcast details")
async def get_podcast(
    podcast_id: int,
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    return podcast

@router.delete("/{podcast_id}", description="Delete a podcast")
async def delete_podcast(
    podcast_id: int,
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Delete from Cloudinary
    try:
        await delete_audio(podcast.file_path)
        for key_point in podcast.key_points:
            await delete_audio(key_point.file_path)
    except Exception as e:
        print(f"Error deleting files from Cloudinary: {str(e)}")
    
    # Delete from database
    db.delete(podcast)
    db.commit()
    
    return {"message": "Podcast deleted successfully"} 

@router.get("/key-points/{key_point_id}/share/facebook", description="Get Facebook share URL for a key point")
async def share_key_point_facebook(
    key_point_id: int,
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    # Get the key point and its associated podcast
    key_point = db.query(KeyPoint).join(Podcast).filter(
        KeyPoint.id == key_point_id,
        Podcast.owner_id == current_user.id
    ).first()
    
    if not key_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key point not found"
        )
    
    # Create share content
    title = f"Key Point from {key_point.podcast.title}"
    description = key_point.content
    audio_url = key_point.file_path
    
    # Create Facebook share URL
    share_url = "https://www.facebook.com/sharer/sharer.php?" + \
                f"u={quote(audio_url)}&" + \
                f"quote={quote(description)}&" + \
                f"title={quote(title)}"
    
    return {"share_url": share_url} 