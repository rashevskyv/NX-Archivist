import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

async def main():
    print("--- Генератор Session String для Telethon ---")
    
    # Load from .env if exists
    load_dotenv()
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    
    if not api_id or not api_hash:
        print("❌ Помилка: API_ID або API_HASH не знайдено в .env")
        api_id = input("Введіть вашій API_ID: ")
        api_hash = input("Введіть вашій API_HASH: ")
    else:
        print(f"✅ Використовую API_ID: {api_id} з файлу .env")

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session_string = client.session.save()
        print("\n" + "="*50)
        print("ВАШ SESSION_STRING (скопіюйте його повністю):")
        print("="*50)
        print(session_string)
        print("="*50)
        print("\nТепер вставте цей рядок у файл .env:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n❌ Виникла помилка: {e}")
