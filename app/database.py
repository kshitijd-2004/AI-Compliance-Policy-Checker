from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict
from .models import Base


class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        extra='ignore', 
        env_file=".env",
        )


settings = Settings()

engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
