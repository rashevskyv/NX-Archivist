from telethon import TelegramClient, events
from app.core.config import config
import os
import asyncio

class Uploader:
    def __init__(self):
        self.client = TelegramClient(
            'nx_archivist_session', 
            config.API_ID, 
            config.API_HASH
        )
        self._phone_hash = None

    async def is_authorized(self) -> bool:
        if not self.client.is_connected():
            await self.client.connect()
        return await self.client.is_user_authorized()

    async def send_code(self, phone: str):
        if not self.client.is_connected():
            await self.client.connect()
        result = await self.client.send_code_request(phone)
        self._phone_hash = result.phone_code_hash
        return result

    async def sign_in(self, phone: str, code: str):
        await self.client.sign_in(phone, code, phone_code_hash=self._phone_hash)

    async def upload_file(self, file_path: str, caption: str = "") -> str:
        """
        Uploads a file to the storage channel and returns the message link.
        """
        if not await self.is_authorized():
            raise Exception("Userbot is not authorized. Use /login command.")

        message = await self.client.send_file(
            config.STORAGE_CHANNEL_ID,
            file_path,
            caption=caption,
            progress_callback=self._progress_callback
        )
        
        channel_id_str = str(config.STORAGE_CHANNEL_ID)
        if channel_id_str.startswith("-100"):
            cid = channel_id_str[4:]
            return f"https://t.me/c/{cid}/{message.id}"
        
        return f"Message ID: {message.id}"

    def _progress_callback(self, current, total):
        pass
