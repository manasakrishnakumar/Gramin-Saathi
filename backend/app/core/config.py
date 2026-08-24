import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Pinecone
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str = Field("gov-documents", env="PINECONE_INDEX_NAME")
    PINECONE_REGION: str = Field("us-east-1", env="PINECONE_REGION")
    
    # Gemini
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    LLM_MODEL: str = "models/gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    
    # LangCache
    # LangCache
    LANGCACHE_SERVER_URL: str = "https://aws-us-east-1.langcache.redis.io"
    LANGCACHE_CACHE_ID: str | None = None
    LANGCACHE_API_KEY: str | None = None
    
    # Scraping
    SCRAPE_SCHEDULE: str = "0 2 * * *"  # 2 AM daily
    GOV_SITES: str = "https://scholarships.gov.in/All-Scholarships"
    
    # Cache
    MAX_LOCAL_CACHE: int = 50
    MAX_LOCAL_CACHE: int = 50
    CACHE_TTL: int = 86400
    
    # Sarvam AI
    SARVAM_API_KEY: str | None = Field(None, env="SARVAM_API_KEY")

    @property
    def LLM_MODEL_FULL(self) -> str:
        """Ensure model name starts with models/"""
        if self.LLM_MODEL.startswith("models/") or self.LLM_MODEL.startswith("tunedModels/"):
            return self.LLM_MODEL
        return f"models/{self.LLM_MODEL}"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
