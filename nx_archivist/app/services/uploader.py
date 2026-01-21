from pyrogram import Client
from app.core.config import config
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class Uploader:
    def __init__(self):
        session_name = config.TELEGRAM_SESSION_STRING or "nx_archivist_userbot"
        self.client = Client(
            session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir="."
        )
        self._phone = None
        self._phone_code_hash = None

    async def is_authorized(self) -> bool:
        if not self.client.is_connected:
            await self.client.connect()
        try:
            return await self.client.get_me() is not None
        except Exception:
            return False

    async def send_code(self, phone: str):
        if not self.client.is_connected:
            await self.client.connect()
        self._phone = phone
        sent_code = await self.client.send_code(phone)
        self._phone_code_hash = sent_code.phone_code_hash
        return sent_code

    async def sign_in(self, phone: str, code: str):
        await self.client.sign_in(phone, self._phone_code_hash, code)

    async def interactive_login(self):
        """
        Performs interactive login in the terminal using Pyrogram.
        """
        await self.client.start()
        me = await self.client.get_me()
        print(f"✅ Авторизація успішна! Ви увійшли як: {me.first_name}")
        await self.client.stop()

    async def upload_file(self, file_path: str, caption: str = "") -> str:
        """
        Uploads a file to the storage channel and returns the message link.
        """
        if not self.client.is_connected:
            await self.client.connect()
            
        if not await self.is_authorized():
            raise Exception("Userbot is not authorized. Run 'python main.py login' in terminal.")

        message = await self.client.send_document(
            chat_id=config.STORAGE_CHANNEL_ID,
            document=file_path,
            caption=caption,
            progress=self._progress_callback
        )
        
        channel_id_str = str(config.STORAGE_CHANNEL_ID)
        # Pyrogram message.link is available for public channels
        if message.link:
            return message.link
            
        # Fallback for private channels
        if channel_id_str.startswith("-100"):
            cid = channel_id_str[4:]
            return f"https://t.me/c/{cid}/{message.id}"
        
        return f"Message ID: {message.id}"

    def _progress_callback(self, current, total):
        # logger.info(f"Uploaded {current}/{total} bytes ({current/total*100:.1f}%)")
        pass

uploader = Uploader()
