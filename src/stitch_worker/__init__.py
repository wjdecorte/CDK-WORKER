from pydantic_settings import BaseSettings, SettingsConfigDict


class StitchWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    lambda_image_tag: str
