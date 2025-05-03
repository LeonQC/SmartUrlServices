from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """Base user model with common attributes"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    """User registration model with password"""
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    """User information returned to clients"""
    id: int
    created_at: str

    class Config:
        orm_mode = True