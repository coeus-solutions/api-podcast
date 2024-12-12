# Podcast Management API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

### Register New User
```http
POST /auth/signup
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "strongpassword123",
    "name": "John Doe"
}
```

Response:
```json
{
    "email": "user@example.com",
    "name": "John Doe",
    "id": 1,
    "created_at": "2024-01-10T12:00:00"
}
```

### Login
```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=strongpassword123
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Get User Info
```http
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:
```json
{
    "email": "user@example.com",
    "name": "John Doe",
    "id": 1,
    "created_at": "2024-01-10T12:00:00"
}
```

### Update User Name
```http
PUT /auth/me
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
    "name": "New Name"
}
```

Response:
```json
{
    "email": "user@example.com",
    "name": "New Name",
    "id": 1,
    "created_at": "2024-01-10T12:00:00"
}
```

## Podcasts

All podcast endpoints require authentication. Include the token in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Upload Podcast
```http
POST /podcasts
Content-Type: multipart/form-data

{
    "title": "My Awesome Podcast",
    "file": <audio_file.mp3>
}
```

Response:
```json
{
    "id": 1,
    "title": "My Awesome Podcast",
    "file_path": "uploads/my_awesome_podcast_1.mp3",
    "transcript": "This is the transcribed text of the podcast...",
    "created_at": "2024-01-10T12:00:00",
    "owner_id": 1,
    "key_points": [
        {
            "id": 1,
            "content": "First key point",
            "start_time": 0,
            "end_time": 30,
            "file_path": "uploads/clips/clip_1_0_30.mp3",
            "podcast_id": 1,
            "created_at": "2024-01-10T12:00:00"
        }
    ]
}
```

### List All Podcasts
```http
GET /podcasts
```

Response:
```json
[
    {
        "id": 1,
        "title": "My Awesome Podcast",
        "file_path": "uploads/my_awesome_podcast_1.mp3",
        "transcript": "This is the transcribed text of the podcast...",
        "created_at": "2024-01-10T12:00:00",
        "owner_id": 1,
        "key_points": [
            {
                "id": 1,
                "content": "First key point",
                "start_time": 0,
                "end_time": 30,
                "file_path": "uploads/clips/clip_1_0_30.mp3",
                "podcast_id": 1,
                "created_at": "2024-01-10T12:00:00"
            }
        ]
    }
]
```

### Get Single Podcast
```http
GET /podcasts/{podcast_id}
```

Response:
```json
{
    "id": 1,
    "title": "My Awesome Podcast",
    "file_path": "uploads/my_awesome_podcast_1.mp3",
    "transcript": "This is the transcribed text of the podcast...",
    "created_at": "2024-01-10T12:00:00",
    "owner_id": 1,
    "key_points": [
        {
            "id": 1,
            "content": "First key point",
            "start_time": 0,
            "end_time": 30,
            "file_path": "uploads/clips/clip_1_0_30.mp3",
            "podcast_id": 1,
            "created_at": "2024-01-10T12:00:00"
        }
    ]
}
```

### Delete Podcast
```http
DELETE /podcasts/{podcast_id}
```

Response:
```json
{
    "message": "Podcast deleted successfully"
}
```

### Share Key Point on Facebook
```http
GET /podcasts/key-points/{key_point_id}/share/facebook
```

Response:
```json
{
    "share_url": "https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Fexample.com%2Faudio.mp3&quote=This%20is%20a%20key%20point&title=Key%20Point%20from%20My%20Podcast"
}
```

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Invalid file type. Allowed types: audio/mpeg, audio/mp3"
}
```

### 401 Unauthorized
```json
{
    "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
    "detail": "Podcast not found"
}
```

### 500 Internal Server Error
```json
{
    "detail": "Error message describing what went wrong"
}
```

## File Upload Requirements

- Maximum file size: 100MB
- Allowed audio types: audio/mpeg, audio/mp3

## Notes for Frontend Integration

1. Authentication:
   - Store the access token securely (e.g., in HttpOnly cookies or secure local storage)
   - Include the token in all API requests
   - Handle token expiration and refresh

2. File Upload:
   - Use FormData for podcast uploads
   - Show upload progress
   - Handle large file uploads gracefully

3. Audio Playback:
   - Use HTML5 audio player or a library like Wavesurfer.js
   - Support seeking to specific timestamps for key points
   - Handle audio streaming efficiently

4. Error Handling:
   - Show appropriate error messages to users
   - Implement retry mechanisms for failed uploads
   - Handle network errors gracefully

5. Social Sharing:
   - Open Facebook share URLs in a new window/popup
   - Handle the return from social sharing gracefully
   - Provide feedback on successful shares

## Example React Code

```typescript
// Example API client setup
const api = axios.create({
    baseURL: 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add auth token to requests
api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Example upload function
const uploadPodcast = async (title: string, file: File) => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);

    try {
        const response = await api.post('/podcasts', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return response.data;
    } catch (error) {
        handleError(error);
    }
};

// Example share function
const shareKeyPoint = async (keyPointId: number) => {
    try {
        const response = await api.get(`/podcasts/key-points/${keyPointId}/share/facebook`);
        window.open(response.data.share_url, '_blank');
    } catch (error) {
        handleError(error);
    }
};