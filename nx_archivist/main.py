import asyncio
import logging
import sys

# Setup logging immediately to catch import errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)
bot_instance = None

try:
    from app.core.config import config
    from app.utils.storage import get_best_storage_path
    from app.db.base import init_db
except Exception as e:
    if "ValidationError" in str(type(e).__name__):
        logger.error("\n" + "!"*60)
        logger.error("ПОМИЛКА КОНФІГУРАЦІЇ: Відсутні або неправильні дані у файлі .env")
        logger.error("Переконайтеся, що ви створили файл .env та заповнили всі обов'язкові поля:")
        logger.error("BOT_TOKEN, API_ID, API_HASH, STORAGE_CHANNEL_ID, ENCRYPTION_PASSWORD")
        logger.error(f"\nДеталі помилки:\n{e}")
        logger.error("!"*60 + "\n")
    else:
        logger.exception(f"Unexpected error during import: {e}")
    sys.exit(1)

async def main():
    try:
        from aiogram import Bot, Dispatcher
        from app.bot.handlers import search_router, auth_router
    except ImportError as e:
        if "libtorrent" in str(e) or "DLL load failed" in str(e):
            logger.error("\n" + "="*60)
            logger.error("ПОМИЛКА: Не вдалося завантажити libtorrent (DLL load failed).")
            logger.error("Це зазвичай означає, що у вас не встановлено Microsoft Visual C++ Redistributable.")
            logger.error("Будь ласка, завантажте та встановіть його за цим посиланням:")
            logger.error("https://aka.ms/vs/17/release/vc_redist.x64.exe")
            logger.error("="*60 + "\n")
        else:
            logger.exception(f"Failed to import bot modules: {e}")
        sys.exit(1)

    try:
        logger.info("Starting bot initialization...")
        logger.info(f"[CONFIG] Telegram Premium: {config.IS_TELEGRAM_PREMIUM}")
        logger.info(f"[CONFIG] Storage Channel ID: {config.STORAGE_CHANNEL_ID}")
        
        # Initialize DB
        await init_db()
        logger.info("Database initialized.")
        
        # Initialize storage
        if not config.DOWNLOAD_DIR:
            config.DOWNLOAD_DIR = get_best_storage_path()
        logger.info(f"Storage initialized at: {config.DOWNLOAD_DIR}")

        # Initialize Bot and Dispatcher
        bot = Bot(token=config.BOT_TOKEN.get_secret_value())
        global bot_instance
        bot_instance = bot
        dp = Dispatcher()
        
        # Register routers
        dp.include_router(search_router)
        dp.include_router(auth_router)
        
        # Start polling
        logger.info("Bot started and polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Critical error during bot startup: {e}")
        raise

async def cli_login():
    from app.services.uploader import uploader
    await uploader.interactive_login()

async def cli_test():
    from app.services.uploader import uploader
    await uploader.test_connection()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "login":
            try:
                asyncio.run(cli_login())
            except KeyboardInterrupt:
                pass
        elif command == "logintest":
            try:
                asyncio.run(cli_test())
            except KeyboardInterrupt:
                pass
        else:
            print(f"Unknown command: {command}")
            print("Available commands: login, logintest")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass
