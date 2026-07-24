from __future__ import annotations

import json
import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./sample.db"

    # LLM
    llm_provider: str = "openai"   # openai | gemini | claude
    llm_api_key: str = ""
    llm_model: str = ""            # leave blank for provider default

    # Safety
    enable_write_mode: bool = False
    row_limit: int = 100
    query_timeout: int = 30        # seconds

    # CORS — stored as JSON array string in env, e.g. '["http://localhost:3000"]'
    allowed_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # Parse ALLOWED_ORIGINS from JSON string if set via environment
    @classmethod
    def _parse_origins(cls, v: object) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return ["http://localhost:3000"]

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(
            self,
            "allowed_origins",
            self._parse_origins(self.allowed_origins),
        )


settings = Settings()
