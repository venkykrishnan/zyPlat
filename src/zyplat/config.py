"""Runtime settings. ``ZYPLAT_DATABASE_URL`` selects the database."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZYPLAT_", extra="ignore")

    database_url: str = "sqlite:///./zyplat.db"
