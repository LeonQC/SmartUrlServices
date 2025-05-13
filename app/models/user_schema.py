from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user model with common attributes"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    """User registration model with password"""
    password: str = Field(..., min_length=8)

class UserGoogle(BaseModel):
    """User registration with Google token"""
    token: str

class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str

class UserResponse(UserBase):
    """User information returned to clients"""
    id: int
    created_at: str
    auth_provider: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT token response model"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token"""
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    """Response for token refresh"""
    access_token: str
    token_type: str
    expires_in: int

class UserProfileResponse(UserResponse):
    """Extended user profile with statistics"""
    stats: dict

class UserProfileUpdate(BaseModel):
    """User profile update model"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class DeleteAccountRequest(BaseModel):
    """Account deletion confirmation"""
    password: str = Field(..., description="Current password to confirm deletion")