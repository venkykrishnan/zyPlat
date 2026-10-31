from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "zyPlat"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql://zyplat:zyplat@localhost:5432/zyplat"

    # Container filesystems are ephemeral; point this at a persistent volume in deployments.
    INSTANCE_DATA_DIR: str = "./data/instance-data"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
