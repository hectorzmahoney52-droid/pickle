import os
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    BINANCE_API_URL: str = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    OKX_API_URL: str = "https://www.okx.com/v3/c2c/tradingOrders/books"

    # Request settings
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    ADS_COUNT: int = 5

    # Binance currency pairs
    BINANCE_FIATS: list[str] = ["KGS", "KZT", "GEL", "AED", "CNY"]

    # OKX currency pairs
    OKX_FIATS: list[str] = ["UZS"]

    # Logging
    LOG_FILE: str = "logs/bot.log"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
