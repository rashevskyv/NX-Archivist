import asyncio
import os
from pyrogram import Client

async def main():
    print("--- Конвертер .session файлу в Session String ---")
    
    session_name = input("Введіть назву вашого файлу сесії (без .session): ")
    api_id = input("Введіть API_ID: ")
    api_hash = input("Введіть API_HASH: ")
    
    if not os.path.exists(f"{session_name}.session"):
        print(f"❌ Помилка: Файл {session_name}.session не знайдено!")
        return

    async with Client(session_name, api_id=int(api_id), api_hash=api_hash) as app:
        session_string = await app.export_session_string()
        print("\n" + "="*50)
        print("ВАШ SESSION_STRING:")
        print("="*50)
        print(session_string)
        print("="*50)
        print("\nТепер вставте цей рядок у файл .env:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")

if __name__ == "__main__":
    asyncio.run(main())
