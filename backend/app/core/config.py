import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Rakthasethu API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database Configuration (Purely driven by DATABASE_URL, no hardcoded ports)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/rakthasethu"
    DATABASE_ECHO: bool = False

    @field_validator("DATABASE_URL", mode="before")
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            # Render PostgreSQL URLs typically start with postgres:// or postgresql://
            # SQLAlchemy async engine requires postgresql+asyncpg://
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # JWT & Auth
    JWT_SECRET_KEY: str = "dev-secret-key-rakthasethu"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        return []

    # Cooldown Rules (in days)
    WHOLE_BLOOD_COOLDOWN_DAYS: int = 90
    PLATELET_COOLDOWN_DAYS: int = 14
    PLASMA_COOLDOWN_DAYS: int = 28

    # Bulk Import Limits
    MAX_IMPORT_FILE_SIZE_MB: int = 10
    MAX_IMPORT_ROWS: int = 5000

    # Matching Engine Limits
    DEFAULT_MATCH_LIMIT: int = 20
    MAX_MATCH_LIMIT: int = 100

    # Proximity / Spatial Matching (in kilometers)
    DEFAULT_PROXIMITY_RADIUS_KM: float = 25.0
    MAX_PROXIMITY_RADIUS_KM: float = 100.0

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
