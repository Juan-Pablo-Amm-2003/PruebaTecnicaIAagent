from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field("agno-fastapi-azure", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")

    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field("2024-08-01-preview", env="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
