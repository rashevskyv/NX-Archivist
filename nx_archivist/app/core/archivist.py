import py7zr
import os
import secrets
import string
import logging
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
                       archive_name: Optional[str] = None) -> List[str]:
        """
        Packs files into a 7z archive with encryption and splits it if necessary.
        """
        if not archive_name:
            archive_name = cls.generate_obfuscated_name()
            
        archive_path = os.path.join(output_dir, f"{archive_name}.7z")
        
        # Determine split size
        limit_gb = 3.9 if config.IS_TELEGRAM_PREMIUM else 1.9
        split_size = int(limit_gb * 1024 * 1024 * 1024)
        
        logger.info(f"Packing archive. Premium: {config.IS_TELEGRAM_PREMIUM}, Limit: {limit_gb}GB ({split_size} bytes)")
        
        # py7zr doesn't support splitting directly during creation in a simple way
        # We might need to create the archive and then split it manually or use a different tool
        # For the prototype, let's assume we create one archive first
        
        filters = [{"id": py7zr.FILTER_LZMA2, "preset": 9}]
        
        with py7zr.SevenZipFile(archive_path, mode='w', 
                                password=config.ENCRYPTION_PASSWORD,
                                filters=filters) as archive:
            for f in source_files:
                if os.path.isdir(f):
                    archive.writeall(f, arcname=os.path.basename(f))
                else:
                    archive.write(f, arcname=os.path.basename(f))
                
        # Splitting logic (if file size > split_size)
        file_size = os.path.getsize(archive_path)
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
                part_num += 1
                
        # Remove the original large archive
        os.remove(archive_path)
        return parts
