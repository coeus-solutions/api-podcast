from openai import OpenAI
from typing import List, Dict, Tuple
import json
import requests
import tempfile
import os
import tiktoken
from app.config import settings
from app.services import stripe_service
from sqlalchemy.orm import Session
from app.models.models import User
from fastapi import HTTPException

def get_token_count(text: str, model: str = "gpt-4") -> int:
    """Calculate the number of tokens in a text string"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Fallback to cl100k_base encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

async def transcribe_audio(file_url: str, db: Session, user: User) -> str:
    """
    Transcribe audio file using OpenAI Whisper API
    """
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    try:
        response = requests.get(file_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            # Calculate actual tokens used for the transcript
            actual_tokens = get_token_count(transcript)
            stripe_service.calculate_tokens_used(actual_tokens, db, user)
            return transcript
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")

async def extract_key_points(transcript: str, video_duration: float, db: Session, user: User) -> list:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    try:
        prompt = f"""
        Please analyze this podcast transcript and extract key points.
        The total duration of the video is exactly {video_duration:.0f} seconds.
        
        For each key point:
        1. Identify the main content/idea
        2. Provide timestamps that:
           - Are within the total duration of {video_duration:.0f} seconds
           - Have segments of 15-30 seconds each
           - Do not overlap with other segments
           - Are in chronological order
        
        Format the response as a list of JSON objects with the following structure:
        [
            {{"content": "key point 1", "start_time": 0, "end_time": 20}},
            {{"content": "key point 2", "start_time": 35, "end_time": 55}}
        ]

        Important rules:
        - Ensure end_time is never greater than {video_duration:.0f}
        - Keep each segment between 15-30 seconds
        - Maintain chronological order
        - No overlapping segments
        - Leave gaps between segments

        Transcript:
        {transcript}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts key points from video transcripts. You ensure timestamps are accurate and within the video duration."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        # Update token usage with actual usage from the response
        actual_tokens = response.usage.total_tokens
        stripe_service.calculate_tokens_used(actual_tokens, db, user)

        # Extract and validate the key points
        key_points = eval(response.choices[0].message.content)
        
        # Validate and adjust timestamps
        validated_points = []
        last_end_time = 0
        
        for point in key_points:
            start_time = max(point["start_time"], last_end_time + 5)
            end_time = min(start_time + 30, video_duration)
            
            if end_time - start_time >= 15:
                validated_points.append({
                    "content": point["content"],
                    "start_time": start_time,
                    "end_time": end_time
                })
                last_end_time = end_time
        
        return validated_points
    except Exception as e:
        print(f"Error extracting key points: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting key points: {str(e)}")

async def transcribe_video(file_url: str, db: Session, user: User) -> str:
    """
    Transcribe video file using OpenAI Whisper API
    """
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    try:
        response = requests.get(file_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, 'rb') as video_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=video_file,
                    response_format="text"
                )
            
            # Calculate actual tokens used for the transcript
            actual_tokens = get_token_count(transcript)
            stripe_service.calculate_tokens_used(actual_tokens, db, user)
            return transcript
        except Exception as e:
            print(f"Error transcribing video content: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error transcribing video content: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"Error transcribing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error transcribing video: {str(e)}") 