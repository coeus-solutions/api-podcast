import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.config import settings, CLOUDINARY_FOLDER

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_video(file_contents: bytes, resource_type: str = "video") -> dict:
    """
    Upload a video file to Cloudinary
    Returns a dictionary containing the public URL and duration of the uploaded file
    """
    try:
        result = cloudinary.uploader.upload(
            file_contents,
            resource_type=resource_type,
            folder=CLOUDINARY_FOLDER,
            format="mp4"
        )
        print("here5")
        return {
            "url": result["secure_url"],
            "duration": result.get("duration", 0)  # Duration in seconds
        }
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
            eager=[transformation],
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