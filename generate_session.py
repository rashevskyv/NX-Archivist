import asyncio
from pyrogram import Client

async def main():
    print("--- Генератор Session String для Pyrogram ---")
    api_id = input("Введіть вашій API_ID: ")
    api_hash = input("Введіть вашій API_HASH: ")
    
    async with Client(":memory:", api_id=int(api_id), api_hash=api_hash) as app:
        session_string = await app.export_session_string()
        print("\n" + "="*50)
        print("ВАШ SESSION_STRING (скопіюйте його повністю):")
        print("="*50)
        print(session_string)
        print("="*50)
        print("\nТепер вставте цей рядок у файл .env:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")

if __name__ == "__main__":
    asyncio.run(main())
