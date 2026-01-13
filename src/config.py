from typing import List

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Configuration
    app_name: str = Field(default="TodoApp API")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # Database Configuration
    database_url: PostgresDsn = Field(...)

    # JWT Authentication
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1)

    # ✅ CORS Configuration (FINAL – NO VALIDATOR)
    cors_origins: List[str] = Field(
        default=[
            "https://hackathon-2-phase-2-rho.vercel.app",
            "http://localhost:3000",
        ]
    )

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, ge=1)

    # Security
    force_https: bool = Field(default=False)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def get_database_url(self) -> str:
        return str(self.database_url)


settings = Settings()
