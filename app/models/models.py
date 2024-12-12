from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    podcasts = relationship("Podcast", back_populates="owner")

class Podcast(Base):
    __tablename__ = "podcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    file_path = Column(String)
    transcript = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="podcasts")
    key_points = relationship("KeyPoint", back_populates="podcast", cascade="all, delete-orphan")

class KeyPoint(Base):
    __tablename__ = "key_points"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    start_time = Column(Float)  # Start time in seconds
    end_time = Column(Float)    # End time in seconds
    file_path = Column(String)  # Path to the extracted audio clip
    created_at = Column(DateTime, default=datetime.utcnow)
    podcast_id = Column(Integer, ForeignKey("podcasts.id"))
    
    podcast = relationship("Podcast", back_populates="key_points") 