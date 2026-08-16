from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env", "/var/task/.env"),
        extra="ignore",
        protected_namespaces=(),
    )

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    model_mini: str = "gpt-4.1-mini"
    model_flagship: str = "gpt-4.1"
    model_embedding: str = "text-embedding-3-small"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "customer_support"

    jwt_secret: str = "dev-change-me-please"
    jwt_expire_minutes: int = 480

    max_turns: int = 3
    confidence_floor: float = 0.5
    rag_confidence_floor: float = 0.45

    cors_origins: str = "*"


settings = Settings()
