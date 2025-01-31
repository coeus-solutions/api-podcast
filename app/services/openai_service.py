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
import math

def get_token_count(text: str, model: str = "gpt-4") -> int:
    """Calculate the number of tokens in a text string"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Fallback to cl100k_base encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

def split_audio_pydub(file_path: str, chunk_size_mb: int = 24) -> List[str]:
    """
    Split audio file into chunks using pydub
    Returns list of temporary file paths containing the chunks
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("pydub not available, falling back to binary chunking")
        return split_file_binary(file_path, chunk_size_mb)

    try:
        # Load the audio file
        audio = AudioSegment.from_file(file_path)
        
        # Calculate chunk duration in milliseconds
        file_size = os.path.getsize(file_path)
        chunk_duration = math.floor((chunk_size_mb * 1024 * 1024 * len(audio)) / file_size)
        
        chunks = []
        for i in range(0, len(audio), chunk_duration):
            chunk = audio[i:i + chunk_duration]
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_chunk:
                chunk.export(temp_chunk.name, format="mp3")
                chunks.append(temp_chunk.name)
        
        return chunks
    except Exception as e:
        print(f"Error using pydub: {str(e)}, falling back to binary chunking")
        return split_file_binary(file_path, chunk_size_mb)

def split_file_binary(file_path: str, chunk_size_mb: int = 24) -> List[str]:
    """
    Fallback function to split a file into chunks without audio processing
    Returns list of temporary file paths containing the chunks
    """
    chunk_size = chunk_size_mb * 1024 * 1024  # Convert MB to bytes
    chunks = []
    
    with open(file_path, 'rb') as file:
        chunk_number = 0
        while True:
            chunk_data = file.read(chunk_size)
            if not chunk_data:
                break
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{chunk_number}.bin') as temp_chunk:
                temp_chunk.write(chunk_data)
                chunks.append(temp_chunk.name)
            chunk_number += 1
    
    return chunks

async def transcribe_audio(file_url: str, db: Session, user: User) -> str:
    """
    Transcribe audio file using OpenAI Whisper API
    Handles files larger than 25MB by splitting them into chunks
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
            # Check file size
            file_size = os.path.getsize(temp_file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB in bytes
                chunks = split_audio_pydub(temp_file_path)
                transcripts = []
                
                for chunk_path in chunks:
                    try:
                        with open(chunk_path, 'rb') as audio_chunk:
                            chunk_transcript = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_chunk,
                                response_format="text"
                            )
                            transcripts.append(chunk_transcript)
                    except Exception as e:
                        print(f"Error processing chunk {chunk_path}: {str(e)}")
                        continue
                    finally:
                        if os.path.exists(chunk_path):
                            os.remove(chunk_path)
                
                if not transcripts:
                    raise HTTPException(status_code=500, detail="Failed to transcribe any part of the audio")
                
                transcript = " ".join(transcripts)
            else:
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
        
        Return ONLY a valid JSON array with no additional text, formatted exactly like this:
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
        - Return ONLY the JSON array, NO TEXT SHOULD APPEAR BEFORE OR AFTER THE JSON ARRAY
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts key points from video transcripts. You ensure timestamps are accurate and within the video duration. You always return valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500, # Request JSON response
        )

        # Update token usage with actual usage from the response
        actual_tokens = response.usage.total_tokens
        stripe_service.calculate_tokens_used(actual_tokens, db, user)

        # Parse the response as JSON
        try:
            print(f"response: {response.choices[0].message.content}")
            response_content = response.choices[0].message.content.strip()
            key_points = json.loads(response_content)
            
            if not isinstance(key_points, list):
                raise ValueError("Response is not a JSON array")
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to parse key points from response")
        
        # Validate and adjust timestamps
        validated_points = []
        last_end_time = 0
        
        for point in key_points:
            # Validate point structure
            if not all(k in point for k in ("content", "start_time", "end_time")):
                continue
                
            try:
                start_time = float(point["start_time"])
                end_time = float(point["end_time"])
            except (ValueError, TypeError):
                continue
                
            start_time = max(start_time, last_end_time + 5)
            end_time = min(start_time + 30, video_duration)
            
            if end_time - start_time >= 15:
                validated_points.append({
                    "content": str(point["content"]),
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
    Handles files larger than 25MB by splitting them into chunks
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
            # Check file size
            file_size = os.path.getsize(temp_file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB in bytes
                try:
                    from pydub import AudioSegment
                    # Extract audio from video
                    audio = AudioSegment.from_file(temp_file_path, format="mp4")
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as audio_file:
                        audio.export(audio_file.name, format="mp3")
                        chunks = split_audio_pydub(audio_file.name)
                    os.remove(audio_file.name)
                except ImportError:
                    print("pydub not available, falling back to binary chunking")
                    chunks = split_file_binary(temp_file_path)
                
                transcripts = []
                for chunk_path in chunks:
                    try:
                        with open(chunk_path, 'rb') as chunk_file:
                            chunk_transcript = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=chunk_file,
                                response_format="text"
                            )
                            transcripts.append(chunk_transcript)
                    except Exception as e:
                        print(f"Error processing chunk {chunk_path}: {str(e)}")
                        continue
                    finally:
                        if os.path.exists(chunk_path):
                            os.remove(chunk_path)
                
                if not transcripts:
                    raise HTTPException(status_code=500, detail="Failed to transcribe any part of the video")
                
                transcript = " ".join(transcripts)
            else:
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
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"Error transcribing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error transcribing video: {str(e)}") 