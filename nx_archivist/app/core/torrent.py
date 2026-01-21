import libtorrent as lt
import time
import os
import asyncio
from typing import List, Dict, Optional
from app.core.config import config
from app.db.base import async_session
from app.db.models import FilesRegistry, TelegramStorage
from sqlalchemy import select

class TorrentManager:
    def __init__(self):
        self.ses = lt.session({'listen_interfaces': '0.0.0.0:6881'})
        self.downloads = {}

    async def add_torrent(self, torrent_data: bytes, save_path: str) -> Optional[lt.torrent_handle]:
        info = lt.torrent_info(lt.bdecode(torrent_data))
        params = {
            'save_path': save_path,
            'ti': info,
        }
        handle = self.ses.add_torrent(params)
        
        # Initial state: pause and set all priorities to 0 (don't download)
        handle.pause()
        for i in range(info.num_files()):
            handle.file_priority(i, 0)
            
        return handle

    async def check_deduplication(self, handle: lt.torrent_handle) -> List[Dict]:
        """
        Checks which files in the torrent already exist in the database.
        Returns a list of file info with 'exists' flag and 'link' if exists.
        """
        info = handle.get_torrent_info()
        files_status = []
        
        async with async_session() as session:
            for i in range(info.num_files()):
                f = info.file_at(i)
                # Check by name and size (basic deduplication)
                stmt = select(FilesRegistry).where(
                    FilesRegistry.file_original_name == f.path,
                    FilesRegistry.file_size == f.size
                )
                result = await session.execute(stmt)
                db_file = result.scalar_one_or_none()
                
                status = {
                    "index": i,
                    "name": f.path,
                    "size": f.size,
                    "exists": False,
                    "link": None
                }
                
                if db_file:
                    # Get the telegram link
                    stmt_storage = select(TelegramStorage).where(TelegramStorage.file_id == db_file.id)
                    res_storage = await session.execute(stmt_storage)
                    storage = res_storage.scalar_one_or_none()
                    
                    status["exists"] = True
                    if storage:
                        status["link"] = storage.telegram_message_link
                
                files_status.append(status)
                
        return files_status

    async def start_selective_download(self, handle: lt.torrent_handle, file_indices: List[int]):
        """
        Starts downloading only the specified files.
        """
        for idx in file_indices:
            handle.file_priority(idx, 4) # Default priority
            
        handle.resume()
        
        # Wait for download to complete (simplified)
        while not handle.status().is_seeding:
            s = handle.status()
            print(f'\r{s.progress * 100:.2f}% complete (down: {s.download_rate / 1000:.1f} kB/s up: {s.upload_rate / 1000:.1f} kB/s peers: {s.num_peers})', end='')
            await asyncio.sleep(1)
        
        print(f'\n{handle.name()} complete')

    def get_file_path(self, handle: lt.torrent_handle, index: int) -> str:
        info = handle.get_torrent_info()
        return os.path.join(handle.save_path(), info.file_at(index).path)
