from openai import OpenAI
from typing import List, Dict, Tuple
import json
import requests
import tempfile
import os
from app.config import settings



async def transcribe_audio(file_url: str) -> str:
    """
    Transcribe audio file using OpenAI Whisper API
    """
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    try:
        # Download the file from Cloudinary
        response = requests.get(file_url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            # Transcribe the temporary file
            with open(temp_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        raise

async def extract_key_points(transcript: str, video_duration: float) -> list:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    """
    Extract key points from transcript using OpenAI GPT-4
    """
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

        # Extract and validate the key points
        key_points = eval(response.choices[0].message.content)
        
        # Validate and adjust timestamps
        validated_points = []
        last_end_time = 0
        
        for point in key_points:
            # Ensure chronological order and no overlaps
            start_time = max(point["start_time"], last_end_time + 5)  # 5 second gap minimum
            end_time = min(start_time + 30, video_duration)  # Cap at 30 seconds and total duration
            
            # Only add point if there's enough duration left
            if end_time - start_time >= 15:  # Minimum 15 second clip
                validated_points.append({
                    "content": point["content"],
                    "start_time": start_time,
                    "end_time": end_time
                })
                last_end_time = end_time
        
        return validated_points
    except Exception as e:
        print(f"Error extracting key points: {str(e)}")
        raise

async def transcribe_video(file_url: str) -> str:
    """
    Transcribe video file using OpenAI Whisper API
    """
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    try:
        # Download the file from Cloudinary
        response = requests.get(file_url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            # Transcribe the temporary file
            with open(temp_file_path, 'rb') as video_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=video_file,
                    response_format="text"
                )
            return transcript
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"Error transcribing video: {str(e)}")
        raise 