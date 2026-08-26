"""
User model for authentication and authorization.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import bcrypt

from .database import Base


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class User(Base):
    """User model for the application."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # API Key for programmatic access
    api_key = Column(String(100), unique=True, nullable=True, index=True)
    
    # Settings
    settings = Column(Text, nullable=True)  # JSON string of user preferences
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return _hash_password(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash."""
        return _verify_password(password, self.hashed_password)
    
    def set_password(self, password: str):
        """Set a new password."""
        self.hashed_password = self.hash_password(password)