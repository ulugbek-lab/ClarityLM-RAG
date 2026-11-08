from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings): 
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
    )
    # BaseSettings lets your application load values from environment variables and a .env file, validate their types, and supply defaults.
    app_name: str = 'claritylm_rag'
    log_level: str = 'INFO'

    # Vector database connection
    qdrant_url: str
    qdrant_api_key: str 
    qdrant_collection: str 
    qdrant_timeout:float = 10.0

    # Converts text into numerical vectors
    embedding_model: str 

    # Language model selection and execution
    llm_model: str 
    llm_adapter_path: str | None = None
    llm_device: str = 'cpu'
    llm_max_new_tokens: int
    llm_temperature: float = 0.2

    # Intended RAG behavior
    rag_enabled: bool = True
    rag_mode: str = 'auto'

    # Intended retrieval filtering
    top_k: int = 5
    max_context_chars: int = 4000 # max content charcters
    min_score: float = 0.25
    min_score_strict: float = 0.35
    max_sources: int = 2

    # Intended document chunking
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    qdrant_timeout: float = 10.0


# settings = Settings()
