from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=False,
        extra='ignore',
    )

    app_name: str = 'claritylm_rag'
    log_level: str = 'INFO'

    qdrant_url: str
    qdrant_api_key: str | None = None
    qdrant_collection: str = 'claritylm_documents'
    qdrant_timeout: float = 10.0

    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    llm_model: str = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'
    llm_adapter_path: str | None = './clarityLM'
    llm_device: str = 'cpu'
    llm_max_new_tokens: int = 256
    llm_temperature: float = 0.2

    rag_enabled: bool = True
    rag_mode: str = 'auto'  # Backward compatibility; API use_rag takes precedence
    top_k: int = 5
    max_context_chars: int = 4000
    min_score: float = 0.25
    min_score_strict: float = 0.35
    max_sources: int = 2
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200

    # Never expose unrestricted server filesystem ingestion to public users.
    enable_ingest_path: bool = False
