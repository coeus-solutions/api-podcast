from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import aiofiles
import datetime
from urllib.parse import quote
from datetime import timedelta

from app.database import get_db
from app.models.models import User, Podcast, KeyPoint
from app.schemas.schemas import PodcastCreate, Podcast as PodcastSchema, KeyPoint as KeyPointSchema
from app.routers.auth import get_current_user
from app.services.openai_service import transcribe_video, extract_key_points
from app.services.storage_service import upload_video, create_video_clip, delete_video, get_signed_url
from app.config import settings, ALLOWED_MEDIA_TYPES, MAX_FILE_SIZE

router = APIRouter()

# Create upload directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def check_token_balance(user: User, required_tokens: int):
    """Check if user has enough tokens and raise HTTPException if insufficient"""
    try:
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
            
        if user.total_tokens is None:
            user.total_tokens = 0
        if user.used_tokens is None:
            user.used_tokens = 0
            
        available_tokens = user.total_tokens - user.used_tokens
        if available_tokens < required_tokens:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. You need {required_tokens} tokens but have {available_tokens} available. Please purchase more tokens."
            )
    except Exception as e:
        print(f"Error checking token balance: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking token balance")

@router.post("/", response_model=PodcastSchema, description="Upload a new podcast")
async def create_podcast(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    # Validate file type
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_MEDIA_TYPES)}"
        )

    try:
        # Estimate token usage for transcription (approximately 1 token per second)
        estimated_tokens = 600  # Base estimate for a short video
        check_token_balance(current_user, estimated_tokens)
        
        # Read file contents
        file_contents = await file.read()
        if len(file_contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE/1024/1024}MB"
            )
        
        # Upload to Supabase Storage
        upload_result = await upload_video(file_contents)
        video_filename = upload_result["filename"]
        video_duration = upload_result["duration"]
        
        # Get signed URL for the video (valid for 1 hour for transcription)
        video_url = get_signed_url(video_filename, timedelta(hours=1))
        
        # Create podcast record
        db_podcast = Podcast(
            title=title,
            file_path=video_filename,  # Store only filename in database
            owner_id=current_user.id
        )
        db.add(db_podcast)
        db.commit()
        db.refresh(db_podcast)
        
        # Start transcription and key point extraction
        print("starting to transcribe video")
        start_time = datetime.datetime.now()
        transcript = await transcribe_video(video_url, db, current_user)  # Pass the signed URL
        end_time = datetime.datetime.now()
        print(f"transcription took {end_time - start_time} seconds")
        
        print("starting to extract key points")
        start_time = datetime.datetime.now()
        key_points = await extract_key_points(transcript, video_duration, db, current_user)
        end_time = datetime.datetime.now()
        print(f"key point extraction took {end_time - start_time} seconds")
        
        # Update podcast with transcript
        db_podcast.transcript = transcript
        db.commit()
        
        # Create key points
        print("starting to create video clips")
        start_time = datetime.datetime.now()
        for point in key_points:
            clip_filename = await create_video_clip(video_filename, point["start_time"], point["end_time"])
            db_key_point = KeyPoint(
                content=point["content"],
                start_time=point["start_time"],
                end_time=point["end_time"],
                file_path=clip_filename,  # Store only filename in database
                podcast_id=db_podcast.id
            )
            db.add(db_key_point)
        
        db.commit()
        db.refresh(db_podcast)
        end_time = datetime.datetime.now()
        print(f"video clips creation took {end_time - start_time} seconds")
        return db_podcast.to_dict()
        
    except HTTPException as he:
        if he.status_code == 402:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens."
            )
        # If there's an error, try to clean up any created resources
        if 'db_podcast' in locals():
            db.delete(db_podcast)
            db.commit()
        raise he  # Re-raise the HTTP exception
    except Exception as e:
        # If there's an error, try to clean up any created resources
        if 'db_podcast' in locals():
            db.delete(db_podcast)
            db.commit()
        print(f"Error creating podcast: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again."
        )

@router.get("/", response_model=List[PodcastSchema], description="List all podcasts")
async def list_podcasts(
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    podcasts = db.query(Podcast).filter(Podcast.owner_id == current_user.id).all()
    return [podcast.to_dict() for podcast in podcasts]

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
    return podcast.to_dict()

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
    
    # Delete from Supabase Storage
    try:
        await delete_video(podcast.file_path)
        for key_point in podcast.key_points:
            await delete_video(key_point.file_path)
    except Exception as e:
        print(f"Error deleting files from storage: {str(e)}")
    
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

@router.get("/{podcast_id}/key-points", response_model=List[KeyPointSchema], description="Get key points for a podcast")
async def get_podcast_key_points(
    podcast_id: int,
    current_user: User = Security(get_current_user, scopes=[]),
    db: Session = Depends(get_db)
):
    # First check if the podcast exists and belongs to the user
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Get all key points for the podcast
    key_points = db.query(KeyPoint).filter(KeyPoint.podcast_id == podcast_id).all()
    return [kp.to_dict() for kp in key_points] 