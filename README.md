# Podcast Management API

A FastAPI-based REST API for managing podcasts, extracting key points, and creating shareable audio clips.

## Features

- User authentication with JWT tokens
- Upload and manage podcast audio files
- Automatic transcription using OpenAI Whisper API
- Key point extraction using OpenAI GPT-4
- Create and share audio clips from podcasts
- RESTful API design

## Prerequisites

- Python 3.8+
- FFmpeg (for video processing)
- OpenAI API key
- Supabase account and project

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd podcast-management-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# On macOS with Homebrew
brew install ffmpeg

# On Windows with Chocolatey
choco install ffmpeg
```

5. Create a `.env` file in the root directory with the following variables:
```env
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_DB_URL=your-supabase-db-url
SUPABASE_STORAGE_BUCKET=videos
```

6. Set up Supabase:
   - Create a new Supabase project
   - Create a storage bucket named 'videos' with these settings:
     - Set bucket to "private"
     - Enable "Public URLs" feature
   - Configure Storage RLS policies for the 'videos' bucket:
     ```sql
     -- Allow authenticated users to upload files
   - Update your .env file with the Supabase credentials

## Running the API

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation at `http://localhost:8000/docs`

## API Endpoints

### Authentication
- POST `/api/v1/auth/signup` - Create a new user account
- POST `/api/v1/auth/token` - Login and get access token

### Podcasts
- POST `/api/v1/podcasts` - Upload a new podcast
- GET `/api/v1/podcasts` - List all podcasts
- GET `/api/v1/podcasts/{podcast_id}` - Get podcast details
- DELETE `/api/v1/podcasts/{podcast_id}` - Delete a podcast

### Clips
- POST `/api/v1/podcasts/{podcast_id}/clips` - Create a new clip
- GET `/api/v1/podcasts/{podcast_id}/clips` - List all clips for a podcast
- DELETE `/api/v1/podcasts/{podcast_id}/clips/{clip_id}` - Delete a clip

## Project Structure

```
podcast-management-api/
├── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── podcasts.py
│   │   └── clips.py
│   ├── models/
│   │   └── models.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── services/
│   │   └── openai_service.py
│   ├── database.py
│   └── config.py
├── uploads/
├── clips/
├── requirements.txt
├── main.py
└── README.md
```

## Error Handling

The API uses standard HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Security

- JWT-based authentication
- Password hashing with bcrypt
- File type validation
- User ownership validation for all resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 