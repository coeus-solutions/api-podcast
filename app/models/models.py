from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
from app.database import Base
from app.services.storage_service import get_signed_url

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String)
    total_tokens = Column(Integer, default=0)
    used_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    reset_otp = Column(String, nullable=True)
    reset_otp_expiry = Column(DateTime, nullable=True)
    podcasts = relationship("Podcast", back_populates="owner")
    payments = relationship("PaymentHistory", back_populates="user")

    def toDict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "total_tokens": self.total_tokens,
            "used_tokens": self.used_tokens
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "file_path": get_signed_url(self.file_path, timedelta(hours=1)),
            "transcript": self.transcript,
            "created_at": self.created_at,
            "owner_id": self.owner_id
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "file_path": get_signed_url(self.file_path, timedelta(hours=1)),
            "created_at": self.created_at,
            "podcast_id": self.podcast_id
        }

class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    tokens = Column(Integer)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    stripe_session_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="payments") 