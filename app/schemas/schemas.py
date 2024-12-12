from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class KeyPointBase(BaseModel):
    content: str
    start_time: float
    end_time: float

class KeyPointCreate(KeyPointBase):
    pass

class KeyPoint(KeyPointBase):
    id: int
    file_path: str
    podcast_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ClipBase(BaseModel):
    title: str
    start_time: float
    end_time: float

class ClipCreate(ClipBase):
    pass

class Clip(ClipBase):
    id: int
    file_path: str
    podcast_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PodcastBase(BaseModel):
    title: str

class PodcastCreate(PodcastBase):
    pass

class Podcast(PodcastBase):
    id: int
    file_path: str
    transcript: Optional[str]
    created_at: datetime
    owner_id: int
    key_points: List[KeyPoint] = []

    class Config:
        from_attributes = True 