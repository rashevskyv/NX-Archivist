import libtorrent as lt
import time
import os
import asyncio
import hashlib
from typing import List, Dict, Optional
from app.core.config import config
from app.db.base import async_session
from app.db.models import FilesRegistry, TelegramStorage
import logging
from sqlalchemy import select

logger = logging.getLogger(__name__)

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
        Checks which files/folders in the torrent already exist in the database.
        Groups files into folders if a directory contains > 4 files.
        """
        info = handle.get_torrent_info()
        
        # 1. Group files by directory
        dir_map = {} # path -> list of file indices
        for i in range(info.num_files()):
            f = info.file_at(i)
            dirname = os.path.dirname(f.path)
            if dirname not in dir_map:
                dir_map[dirname] = []
            dir_map[dirname].append(i)
            
        final_entities = []
        
        async with async_session() as session:
            # 2. Process each directory
            for dirname, indices in dir_map.items():
                # If it's a folder with > 4 files, treat as one entity
                if dirname and len(indices) > 4:
                    # Calculate stable hash for the folder
                    # Sort indices by path to ensure stability
                    sorted_indices = sorted(indices, key=lambda idx: info.file_at(idx).path)
                    hash_input = ""
                    total_size = 0
                    for idx in sorted_indices:
                        f = info.file_at(idx)
                        # We use path and size for stable hashing
                        hash_input += f"{f.path}|{f.size}|"
                        total_size += f.size
                    
                    folder_hash = hashlib.sha256(hash_input.encode()).hexdigest()
                    
                    # Check DB for this folder hash
                    stmt = select(FilesRegistry).where(
                        FilesRegistry.file_hash == folder_hash
                    )
                    result = await session.execute(stmt)
                    db_folder = result.scalar_one_or_none()
                    
                    status = {
                        "is_folder": True,
                        "name": dirname,
                        "size": total_size,
                        "indices": indices,
                        "exists": False,
                        "link": None,
                        "hash": folder_hash
                    }
                    
                    if db_folder:
                        stmt_storage = select(TelegramStorage).where(TelegramStorage.file_id == db_folder.id)
                        res_storage = await session.execute(stmt_storage)
                        storage = res_storage.scalar_one_or_none()
                        status["exists"] = True
                        if storage:
                            status["link"] = storage.telegram_message_link
                            
                    final_entities.append(status)
                else:
                    # Treat files individually
                    for i in indices:
                        f = info.file_at(i)
                        # Check by name and size
                        stmt = select(FilesRegistry).where(
                            FilesRegistry.file_original_name == f.path,
                            FilesRegistry.file_size == f.size
                        )
                        result = await session.execute(stmt)
                        db_file = result.scalar_one_or_none()
                        
                        status = {
                            "is_folder": False,
                            "index": i,
                            "name": f.path,
                            "size": f.size,
                            "exists": False,
                            "link": None
                        }
                        
                        if db_file:
                            stmt_storage = select(TelegramStorage).where(TelegramStorage.file_id == db_file.id)
                            res_storage = await session.execute(stmt_storage)
                            storage = res_storage.scalar_one_or_none()
                            status["exists"] = True
                            if storage:
                                status["link"] = storage.telegram_message_link
                        
                        final_entities.append(status)
                        
        return final_entities

    async def start_selective_download(self, handle: lt.torrent_handle, file_indices: List[int], task_id: Optional[str] = None):
        """
        Starts downloading only the specified files.
        """
        from app.core.tasks import task_manager, TaskStatus
        
        for idx in file_indices:
            handle.file_priority(idx, 4) # Default priority
            
        handle.resume()
        
        if task_id:
            task_manager.update_task(task_id, status=TaskStatus.DOWNLOADING)

        # Wait for download to complete
        while not handle.status().is_seeding:
            s = handle.status()
            progress = s.progress * 100
            download_rate = s.download_rate # bytes/s
            
            # Calculate ETA
            eta = 0
            if download_rate > 0:
                remaining_bytes = s.total_wanted - s.total_wanted_done
                eta = remaining_bytes / download_rate

            if task_id:
                task_manager.update_task(
                    task_id, 
                    progress=progress, 
                    speed=download_rate,
                    seeds=s.num_seeds,
                    total_size=s.total_wanted,
                    eta=eta
                )
            
            logger.info(f'[{task_id or "TORRENT"}] {progress:.1f}% | Speed: {download_rate / 1024:.1f} KB/s | Seeds: {s.num_seeds} | Size: {s.total_wanted / (1024**3):.2f} GB | Peers: {s.num_peers}')
            await asyncio.sleep(2) # Reduced frequency for console logs
        
        if task_id:
            task_manager.update_task(task_id, progress=100.0, speed=0.0, eta=0.0)
            
        logger.info(f'{handle.name()} complete')

    def get_file_path(self, handle: lt.torrent_handle, index: int) -> str:
        info = handle.get_torrent_info()
        return os.path.join(handle.save_path(), info.file_at(index).path)
