from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    # Telegram Bot (Aiogram)
    BOT_TOKEN: SecretStr
    
    # Telegram Userbot (Telethon/Pyrogram)
    API_ID: int
    API_HASH: str
    STORAGE_CHANNEL_ID: int
    
    # RuTracker Auth
    RUTRACKER_USER: str | None = None
    RUTRACKER_PASS: str | None = None
    RUTRACKER_COOKIES_FILE: str = "cookies.json"
    
    # Archivist Settings
    ENCRYPTION_PASSWORD: str
    IS_TELEGRAM_PREMIUM: bool = False
    
    # Storage Management
    MAX_STORAGE_GB: int = 200
    DOWNLOAD_DIR: str | None = None  # Will be auto-calculated if None
    DELETE_AFTER_UPLOAD: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nx_archivist.db"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()

def ensure_env_param(param_name: str, default_value: str):
    import os
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            content = f.read()
        if param_name not in content:
            with open(".env", "a", encoding="utf-8") as f:
                f.write(f"\n{param_name}={default_value}\n")
            print(f"[CONFIG] Added missing parameter {param_name} to .env")

# Ensure DELETE_AFTER_UPLOAD exists in .env
ensure_env_param("DELETE_AFTER_UPLOAD", "False")
