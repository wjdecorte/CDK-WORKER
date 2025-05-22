from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


class StitchWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    lambda_image_tag: str
    lambda_block_standardization: bool = True
    lambda_document_summary: bool = False
    lambda_seed_questions: bool = False
    lambda_feature_extraction: bool = False
    lambda_document_extraction: bool = True
    lambda_split_file: bool = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return dotenv_settings, env_settings, init_settings
