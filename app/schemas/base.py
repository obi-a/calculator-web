from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional


class UserBase(BaseModel):
    """Base user schema with common fields"""
    first_name: Optional[str] = Field(default=None, max_length=50, example="John")
    last_name: Optional[str] = Field(default=None, max_length=50, example="Doe")
    email: EmailStr = Field(example="john.doe@example.com")
    username: str = Field(min_length=3, max_length=50, example="johndoe")

    model_config = ConfigDict(from_attributes=True)


class PasswordMixin(BaseModel):
    """Mixin for password validation"""
    password: str = Field(min_length=6, max_length=128, example="SecurePass123")

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not any(char.isupper() for char in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must contain at least one digit")
        return password


class UserCreate(UserBase, PasswordMixin):
    """Schema for user creation"""
    pass


class UserLogin(PasswordMixin):
    """Schema for user login"""
    username: str = Field(
        description="Username or email",
        min_length=3,
        max_length=50,
        example="johndoe123"
    )
