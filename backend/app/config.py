from __future__ import annotations

import json
import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./sample.db"

    # LLM
    llm_provider: str = "openai"   # openai | groq | gemini | claude
    llm_api_key: str = ""
    llm_model: str = ""

    # Safety
    enable_write_mode: bool = False
    row_limit: int = 100
    query_timeout: int = 30

    # CORS — accepts either JSON array or comma-separated string
    # e.g.  '["https://foo.vercel.app"]'  OR  'https://foo.vercel.app,http://localhost:3000'
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_allowed_origins(self) -> List[str]:
        raw = self.allowed_origins.strip()
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
