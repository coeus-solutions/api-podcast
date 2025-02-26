from supabase import create_client, Client
import tempfile
import os
import subprocess
from typing import Union, Dict
from app.config import settings
import uuid
from fastapi import HTTPException
import requests
from datetime import timedelta

# Initialize Supabase client with service role key for storage operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_signed_url(filename: str, expiry_duration: timedelta = timedelta(hours=1)) -> str:
    try:
        result = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(
            path=filename,
            expires_in=int(expiry_duration.total_seconds())
        )
        return result['signedURL']
    except Exception as e:
        print(f"Error getting signed URL: {str(e)}")
        return filename

def _get_video_duration(file_path: str) -> float:
    """
    Get video duration using FFmpeg
    """
    try:
        result = subprocess.run([
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            file_path
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting video duration: {str(e)}")
        return 0.0

    """
    Download a file from a URL to a temporary file
    Returns the path to the temporary file
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create a temporary file with the correct extension
        suffix = '.mp4'  # Default to .mp4
        if 'content-type' in response.headers:
            if response.headers['content-type'] == 'video/quicktime':
                suffix = '.mov'
            elif response.headers['content-type'] == 'video/x-msvideo':
                suffix = '.avi'
            elif response.headers['content-type'] == 'video/webm':
                suffix = '.webm'
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

async def upload_video(file_contents: Union[bytes, str], resource_type: str = "video") -> Dict:
    """
    Upload a video file to Supabase Storage
    Returns a dictionary containing the filename and duration of the uploaded file
    """
    try:
        # If file_contents is a string, assume it's a file path
        if isinstance(file_contents, str):
            file_path = file_contents
            is_temp = False
        else:
            # Create a temporary file from bytes
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file.write(file_contents)
                file_path = temp_file.name
            is_temp = True

        try:
            # Get video duration using FFmpeg
            duration = _get_video_duration(file_path)
            
            # Generate a unique filename
            filename = f"{uuid.uuid4()}.mp4"
            
            # Upload to Supabase Storage
            with open(file_path, 'rb') as file:
                result = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                    path=filename,
                    file=file,
                    file_options={"content-type": "video/mp4"}
                )
            
            return {
                "filename": filename,  # Store only the filename in the database
                "duration": duration
            }
        finally:
            # Clean up temporary file if we created one
            if is_temp and os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print(f"Error uploading to Supabase Storage: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading to Supabase Storage")

async def create_video_clip(source_filename: str, start_time: float, end_time: float) -> str:
    """
    Create a video clip using FFmpeg
    Returns the filename of the generated clip
    """
    source_path = None
    output_path = None
    
    try:
        # Create a temporary file for the source video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_source:
            # Get the file data directly from Supabase Storage
            data = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).download(source_filename)
            temp_source.write(data)
            source_path = temp_source.name

        # Create temporary file for the output clip
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_output:
            output_path = temp_output.name

        # Use FFmpeg to create the clip
        subprocess.run([
            'ffmpeg',
            '-y',  # Force overwrite output file
            '-i', source_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-c:v', 'copy',
            '-c:a', 'copy',
            output_path
        ], check=True)

        # Generate a unique filename for the clip
        clip_filename = f"clip_{uuid.uuid4()}.mp4"

        # Upload the clip to Supabase Storage
        with open(output_path, 'rb') as clip_file:
            supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                path=clip_filename,
                file=clip_file,
                file_options={"content-type": "video/mp4"}
            )

        return clip_filename

    except Exception as e:
        print(f"Error creating video clip: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating video clip")
    finally:
        # Clean up temporary files
        if source_path and os.path.exists(source_path):
            os.remove(source_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

async def delete_video(filename: str):
    """
    Delete a video file from Supabase Storage
    """
    try:
        supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([filename])
        return {"success": True}
    except Exception as e:
        print(f"Error deleting from Supabase Storage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 