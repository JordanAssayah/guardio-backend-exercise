"""
Application configuration from environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class AppConfig(BaseSettings):
    pokeproxy_config: str
    pokeproxy_secret: str
    # Max body size in bytes. Default 4KB (~40x larger than a typical Pokemon message)
    pokeproxy_max_body_size: int = 4096

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
