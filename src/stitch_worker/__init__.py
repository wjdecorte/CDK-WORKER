from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


class StitchWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    lambda_image_tag: str
    lambda_block_standardization: bool = True
    lambda_block_summarization: bool = True
    lambda_block_refinement: bool = True
    lambda_block_insertion: bool = True
    lambda_block_vectorization: bool = True
    lambda_document_summarization: bool = True
    lambda_seed_questions: bool = False
    lambda_feature_extraction: bool = False
    lambda_document_extraction: bool = True
    lambda_split_file: bool = True
    openai_api_key: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index_name: str | None = None
    create_hub_instance: bool = False
    system_admin_api_key: str | None = None
    hub_url: str | None = None
    database_host: str | None = None
    database_port: str | None = None
    database_name: str | None = None
    database_user: str | None = None
    database_password: str | None = None
    embedding_batch_size: str = "100"
    document_summary_max_tokens: str = "1000"
    openai_chat_completion_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

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
