from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    anthropic_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
