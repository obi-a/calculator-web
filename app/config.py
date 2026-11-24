from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
    # Development fallback; the JWT_SECRET_KEY environment variable overrides it.
    JWT_SECRET_KEY: str = "your-secret-key"
    
    class Config:
        env_file = ".env"

settings = Settings()
