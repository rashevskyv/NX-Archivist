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

    async def start(self):
        await self.client.start()

    async def upload_file(self, file_path: str, caption: str = "") -> str:
        """
        Uploads a file to the storage channel and returns the message link.
        """
        async with self.client:
            message = await self.client.send_file(
                config.STORAGE_CHANNEL_ID,
                file_path,
                caption=caption,
                progress_callback=self._progress_callback
            )
            
            # Construct message link
            # For public channels: https://t.me/channel_name/123
            # For private channels: https://t.me/c/123456789/123
            channel_id_str = str(config.STORAGE_CHANNEL_ID)
            if channel_id_str.startswith("-100"):
                cid = channel_id_str[4:]
                return f"https://t.me/c/{cid}/{message.id}"
            
            return f"Message ID: {message.id}"

    def _progress_callback(self, current, total):
        # logging.info(f"Uploaded {current}/{total} bytes ({current/total*100:.1f}%)")
        pass
