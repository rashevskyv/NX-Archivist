from telethon import TelegramClient
from telethon.sessions import StringSession
from app.core.config import config
import os
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class Uploader:
    def __init__(self):
        session = config.TELEGRAM_SESSION_NAME
        if config.TELEGRAM_SESSION_STRING:
            session = StringSession(config.TELEGRAM_SESSION_STRING)
        
        self.client = TelegramClient(
            session,
            api_id=config.API_ID,
            api_hash=config.API_HASH
        )
        self._phone = None

    async def is_authorized(self) -> bool:
        if not self.client.is_connected():
            await self.client.connect()
        return await self.client.is_user_authorized()

    async def send_code(self, phone: str):
        if not self.client.is_connected():
            await self.client.connect()
        self._phone = phone
        return await self.client.send_code_request(phone)

    async def sign_in(self, phone: str, code: str, password: str = None):
        try:
            await self.client.sign_in(phone, code, password=password)
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            raise

    async def interactive_login(self):
        """
        Performs interactive login in the terminal using Telethon.
        """
        await self.client.start()
        me = await self.client.get_me()
        print(f"✅ Авторизація успішна! Ви увійшли як: {me.first_name}")
        await self.client.disconnect()

    async def test_connection(self):
        """
        Tests the connection and authorization status.
        """
        print(f"🔄 Перевірка сесії: {config.TELEGRAM_SESSION_NAME}...")
        try:
            await self.client.connect()
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                print(f"✅ Сесія валідна!")
                print(f"👤 Користувач: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
                print(f"🆔 ID: {me.id}")
            else:
                print("❌ Помилка: Сесія не авторизована.")
            await self.client.disconnect()
        except Exception as e:
            print(f"❌ Помилка перевірки сесії: {e}")
            if "password" in str(e).lower():
                print("💡 Підказка: Потрібен пароль двофакторної аутентифікації (2FA).")
            elif "database is locked" in str(e).lower():
                print("💡 Підказка: Файл сесії заблокований іншим процесом.")

    async def _get_entity(self, entity_id):
        try:
            # Try to get from cache first
            return await self.client.get_entity(entity_id)
        except (ValueError, Exception) as e:
            logger.info(f"Entity {entity_id} not in cache, fetching dialogs... ({e})")
            # If not found in cache, try to find it in dialogs (fetch all)
            async for dialog in self.client.iter_dialogs(limit=None):
                if dialog.id == entity_id:
                    return dialog.entity
            
            # If still not found, try to resolve by marked ID if it's a channel
            if isinstance(entity_id, int) and str(entity_id).startswith("-100"):
                try:
                    # Try to get as PeerChannel
                    from telethon.tl.types import PeerChannel
                    real_id = int(str(entity_id)[4:])
                    return await self.client.get_entity(PeerChannel(real_id))
                except Exception:
                    pass
            
            raise ValueError(f"Could not find entity {entity_id} even after fetching all dialogs. "
                             f"Make sure the account is a member of the channel/group.")

    async def upload_file(self, file_path: str, caption: str = "", task_id: Optional[str] = None) -> str:
        """
        Uploads a file to the storage channel and returns the message link.
        """
        from app.core.tasks import task_manager, TaskStatus
        
        if not self.client.is_connected():
            await self.client.connect()
            
        if not await self.client.is_user_authorized():
            raise Exception("Userbot is not authorized. Run 'python nx_archivist/main.py login' in terminal.")

        if task_id:
            task_manager.update_task(task_id, status=TaskStatus.UPLOADING, progress=0.0)
            self._current_task_id = task_id
            self._last_progress_time = time.time()
            self._last_progress_bytes = 0
        else:
            self._current_task_id = None

        # Resolve entity robustly
        try:
            entity = await self._get_entity(config.STORAGE_CHANNEL_ID)
        except Exception as e:
            logger.error(f"Failed to resolve storage channel {config.STORAGE_CHANNEL_ID}: {e}")
            raise

        message = await self.client.send_file(
            entity,
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
        if hasattr(self, '_current_task_id') and self._current_task_id:
            from app.core.tasks import task_manager
            now = time.time()
            duration = now - self._last_progress_time
            
            if duration >= 1.0: # Update every second
                speed = (current - self._last_progress_bytes) / duration
                progress = (current / total) * 100
                eta = (total - current) / speed if speed > 0 else 0
                
                task_manager.update_task(
                    self._current_task_id,
                    progress=progress,
                    speed=speed,
                    eta=eta
                )
                
                self._last_progress_time = now
                self._last_progress_bytes = current

uploader = Uploader()
