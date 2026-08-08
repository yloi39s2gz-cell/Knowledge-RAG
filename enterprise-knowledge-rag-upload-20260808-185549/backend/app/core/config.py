from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Knowledge RAG"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "sqlite:///./storage/app.db"
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 20
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "knowledge_chunks"
    embedding_dimension: int = 128

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
