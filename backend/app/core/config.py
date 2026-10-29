from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "zyPlat"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql://zyplat:zyplat@localhost:5432/zyplat"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
