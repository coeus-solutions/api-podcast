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

async def extract_key_points(transcript: str) -> list:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    """
    Extract key points from transcript using OpenAI GPT-4
    """
    try:
        prompt = f"""
        Please analyze this podcast transcript and extract the key points.
        For each key point, provide:
        1. The main content/idea
        2. Approximate start time (in seconds)
        3. Approximate end time (in seconds)

        Format the response as a list of JSON objects with the following structure:
        [
            {{"content": "key point 1", "start_time": 0, "end_time": 30}},
            {{"content": "key point 2", "start_time": 31, "end_time": 60}}
        ]

        Transcript:
        {transcript}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts key points from podcast transcripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        # Extract the response content and parse it as a list
        key_points = eval(response.choices[0].message.content)
        return key_points
    except Exception as e:
        print(f"Error extracting key points: {str(e)}")
        raise 