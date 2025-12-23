import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "School POS System"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: str = "*"
    FRONTEND_URL: str = "http://localhost:5173" # Valor por defecto para desarrollo

    PAYU_MERCHANT_ID: str
    PAYU_API_KEY: str
    PAYU_API_LOGIN: str
    PAYU_ACCOUNT_ID: str
    PAYU_IS_TEST: bool = True
    PAYU_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings()