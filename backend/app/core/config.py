from decimal import Decimal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "School POS System"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "*"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    JWT_ISSUER: str = "school-pos"
    JWT_AUDIENCE: str = "school-pos-api"
    AUTH_COOKIE_NAME: str = "school_pos_session"
    CSRF_COOKIE_NAME: str = "school_pos_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    SETTINGS_ENCRYPTION_KEY: str = ""

    NFC_EXECUTABLE_PATH: str = ""
    NFC_EXECUTABLE_VERSION: str = "1.0.0"

    PAYU_MERCHANT_ID: str
    PAYU_API_KEY: str
    PAYU_API_LOGIN: str
    PAYU_ACCOUNT_ID: str
    PAYU_IS_TEST: bool = True
    PAYU_URL: str

    PAYMENT_CURRENCY: str = "COP"
    MIN_RECHARGE_AMOUNT: Decimal = Decimal("1000")
    MAX_RECHARGE_AMOUNT: Decimal = Decimal("500000")
    APP_TIMEZONE: str = "America/Bogota"

    MAX_IMPORT_BYTES: int = 10 * 1024 * 1024
    MAX_UPLOAD_BYTES: int = 2 * 1024 * 1024

    ADMIN_EMAIL: str = ""
    ADMIN_INITIAL_PASSWORD: str = ""
    ADMIN_FORCE_CHANGE: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _validate_environment(self):
        self.PUBLIC_BASE_URL = self.PUBLIC_BASE_URL.rstrip("/")
        self.FRONTEND_URL = self.FRONTEND_URL.rstrip("/")

        if self.ENVIRONMENT.lower() == "production":
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY debe tener al menos 32 caracteres en producción")
            if len(self.SETTINGS_ENCRYPTION_KEY) < 32:
                raise ValueError(
                    "SETTINGS_ENCRYPTION_KEY debe tener al menos 32 caracteres en producción"
                )
            if self.ALLOWED_ORIGINS.strip() == "*":
                raise ValueError("ALLOWED_ORIGINS no puede ser '*' en producción")
            if not self.PUBLIC_BASE_URL.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL debe usar HTTPS en producción")
        return self

    @property
    def use_secure_cookies(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
