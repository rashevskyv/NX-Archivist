import py7zr
import os
import secrets
import string
import logging
import asyncio
from typing import List, Optional
from app.core.config import config

logger = logging.getLogger(__name__)

class Archivist:
    @staticmethod
    def generate_obfuscated_name(length: int = 40) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @classmethod
    def pack_and_split(cls, 
                       source_files: List[str], 
                       output_dir: str, 
                       archive_name: Optional[str] = None,
                       progress_callback: Optional[callable] = None) -> List[str]:
        """
        Packs files into a 7z archive with AES-256 encryption and splits it if necessary.
        """
        if not archive_name:
            archive_name = cls.generate_obfuscated_name()
            
        archive_path = os.path.join(output_dir, f"{archive_name}.7z")
        password = config.ENCRYPTION_PASSWORD
        
        # Determine split size
        limit_gb = 3.9 if config.IS_TELEGRAM_PREMIUM else 1.9
        split_size = int(limit_gb * 1024 * 1024 * 1024)
        
        logger.info(f"Packing 7z archive with AES-256. Premium: {config.IS_TELEGRAM_PREMIUM}, Limit: {limit_gb}GB")
        
        # Calculate total size for progress reporting
        total_size = 0
        all_files = []
        for f in source_files:
            if os.path.isdir(f):
                for root, dirs, files in os.walk(f):
                    for file in files:
                        p = os.path.join(root, file)
                        all_files.append((p, os.path.relpath(p, os.path.dirname(f))))
                        total_size += os.path.getsize(p)
            else:
                all_files.append((f, os.path.basename(f)))
                total_size += os.path.getsize(f)

        current_size = 0
        filters = [{"id": py7zr.FILTER_LZMA2, "preset": 9}]
        
        with py7zr.SevenZipFile(archive_path, 'w', password=password, filters=filters) as archive:
            for full_path, arcname in all_files:
                archive.write(full_path, arcname=arcname)
                current_size += os.path.getsize(full_path)
                if progress_callback and total_size > 0:
                    # Packing is first 50% of the process
                    progress = (current_size / total_size) * 50
                    progress_callback(progress)
                
        # Splitting logic (if file size > split_size)
        file_size = os.path.getsize(archive_path)
        logger.info(f"7z Archive created. Total size: {file_size / (1024**2):.1f} MB")
        
        if file_size <= split_size:
            return [archive_path]
            
        # Split the file
        parts = []
        with open(archive_path, 'rb') as f:
            part_num = 1
            while True:
                chunk = f.read(split_size)
                if not chunk:
                    break
                part_path = f"{archive_path}.{part_num:03d}"
                with open(part_path, 'wb') as part_file:
                    part_file.write(chunk)
                
                parts.append(part_path)
                
                if progress_callback and file_size > 0:
                    # Splitting is the second 50%
                    progress = 50 + (part_num * split_size / file_size) * 50
                    progress_callback(min(progress, 99.9))
                
                part_num += 1
                
        # Remove the original large archive
        os.remove(archive_path)
        return parts
