from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_channel: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
