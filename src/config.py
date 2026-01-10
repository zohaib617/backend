"""
Configuration management for TodoApp Backend API.

This module handles all application configuration using Pydantic Settings,
ensuring type safety and validation of environment variables.
"""

from typing import List

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All sensitive configuration (secrets, database URLs) must be provided
    via environment variables. No secrets should be hardcoded.

    Attributes:
        app_name: Application name for logging and documentation
        app_version: Application version
        environment: Deployment environment (development, staging, production)
        debug: Enable debug mode (should be False in production)
        host: Server host address
        port: Server port number
        database_url: PostgreSQL connection string
        jwt_secret: Secret key for JWT token signing
        jwt_algorithm: Algorithm for JWT token signing
        jwt_access_token_expire_minutes: JWT token expiration time in minutes
        cors_origins: List of allowed CORS origins
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json or text)
        rate_limit_per_minute: Maximum requests per minute per client
        force_https: Enforce HTTPS in production
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Configuration
    app_name: str = Field(default="TodoApp API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Deployment environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Database Configuration
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string (format: postgresql+asyncpg://user:pass@host:port/db)",
    )

    # JWT Authentication
    jwt_secret: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT signing (min 32 characters)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="JWT token expiration in minutes",
    )

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)",
        pattern="^(json|text)$",
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        description="Maximum requests per minute per client",
    )

    # Security
    force_https: bool = Field(
        default=False,
        description="Enforce HTTPS in production",
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """
        Parse comma-separated CORS origins into a list.

        Args:
            v: Comma-separated string of origins

        Returns:
            List of origin URLs

        Raises:
            ValueError: If origins string is empty
        """
        if not v or not v.strip():
            raise ValueError("CORS origins cannot be empty")
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        Validate environment value.

        Args:
            v: Environment string

        Returns:
            Validated environment string

        Raises:
            ValueError: If environment is not valid
        """
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Get CORS origins as a list.

        Returns:
            List of allowed CORS origin URLs
        """
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """
        Check if running in production environment.

        Returns:
            True if environment is production, False otherwise
        """
        return self.environment == "production"

    def get_database_url(self) -> str:
        """
        Get database URL as string.

        Returns:
            Database connection string
        """
        return str(self.database_url)


# Global settings instance
# This will be initialized once and reused throughout the application
settings = Settings()
