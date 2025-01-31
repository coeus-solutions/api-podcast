import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.config import settings, CLOUDINARY_FOLDER
import tempfile
import os
from typing import Union

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def _chunked_upload(file_path: str, chunk_size: int = 20*1024*1024, resource_type: str = "video") -> dict:
    """
    Upload a large file to Cloudinary using chunks
    chunk_size is in bytes (default 20MB)
    """
    file_size = os.path.getsize(file_path)
    
    # Start the upload session
    upload_response = cloudinary.uploader.upload_large(
        file_path,
        resource_type=resource_type,
        folder=CLOUDINARY_FOLDER,
        chunk_size=chunk_size,
        eager=[{"format": "mp4"}],
        eager_async=True,
        eager_notification_url=settings.CLOUDINARY_NOTIFICATION_URL if hasattr(settings, 'CLOUDINARY_NOTIFICATION_URL') else None,
        timeout=None  # Disable timeout for large uploads
    )
    
    return upload_response

async def upload_video(file_contents: Union[bytes, str], resource_type: str = "video") -> dict:
    """
    Upload a video file to Cloudinary
    Handles both small and large files
    Returns a dictionary containing the public URL and duration of the uploaded file
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
            file_size = os.path.getsize(file_path)
            
            if file_size > 100 * 1024 * 1024:  # 100MB
                # Use chunked upload for large files
                result = _chunked_upload(file_path, resource_type=resource_type)
            else:
                # Use regular upload for small files
                with open(file_path, 'rb') as file:
                    result = cloudinary.uploader.upload(
                        file,
                        resource_type=resource_type,
                        folder=CLOUDINARY_FOLDER,
                        eager=[{"format": "mp4"}],
                        eager_async=True,
                        eager_notification_url=settings.CLOUDINARY_NOTIFICATION_URL if hasattr(settings, 'CLOUDINARY_NOTIFICATION_URL') else None,
                        timeout=None  # Disable timeout for large uploads
                    )
            
            return {
                "url": result["secure_url"],
                "duration": result.get("duration", 0)  # Duration in seconds
            }
        finally:
            # Clean up temporary file if we created one
            if is_temp and os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print(f"Error uploading to Cloudinary: {str(e)}")
        raise

async def create_video_clip(source_url: str, start_time: float, end_time: float) -> str:
    """
    Create a video clip from a source video using Cloudinary's transformation capabilities
    Returns the URL of the generated clip
    """
    try:
        # Create a new transformation for the video clip
        transformation = {
            'resource_type': 'video',
            'start_offset': f"{start_time:.2f}",
            'end_offset': f"{end_time:.2f}",
            'format': 'mp4'
        }
        
        # Generate a new URL with the transformation
        public_id = source_url.split('/')[-1].split('.')[0]
        print(source_url)
        result = cloudinary.uploader.upload(
            source_url,
            type="upload",
            resource_type="video",
            eager=[{
                'start_offset': f"{start_time:.2f}",
                'end_offset': f"{end_time:.2f}",
                'format': 'mp4'
            }],
            eager_async=True,
            eager_notification_url=settings.CLOUDINARY_NOTIFICATION_URL if hasattr(settings, 'CLOUDINARY_NOTIFICATION_URL') else None,
            folder=f"{CLOUDINARY_FOLDER}/clips"
        )
        
        # Return the URL of the transformed video
        return result["eager"][0]["secure_url"]
    except Exception as e:
        print(f"Error creating video clip in Cloudinary: {str(e)}")
        raise

async def delete_audio(public_id: str, resource_type: str = "video"):
    """
    Delete an audio file from Cloudinary
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result
    except Exception as e:
        print(f"Error deleting from Cloudinary: {str(e)}")
        raise 