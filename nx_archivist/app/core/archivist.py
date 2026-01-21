import zipfile
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
        Packs files into a ZIP archive and splits it if necessary.
        """
        if not archive_name:
            archive_name = cls.generate_obfuscated_name()
            
        archive_path = os.path.join(output_dir, f"{archive_name}.zip")
        
        # Determine split size
        limit_gb = 3.9 if config.IS_TELEGRAM_PREMIUM else 1.9
        split_size = int(limit_gb * 1024 * 1024 * 1024)
        
        logger.info(f"Packing ZIP archive. Premium: {config.IS_TELEGRAM_PREMIUM}, Limit: {limit_gb}GB ({split_size} bytes)")
        
        # Determine compression based on file types
        compression = zipfile.ZIP_STORED
        compresslevel = None
        
        has_nsp = any(f.lower().endswith('.nsp') for f in source_files)
        if has_nsp:
            compression = zipfile.ZIP_DEFLATED
            compresslevel = 9
            logger.info("NSP detected: using ZIP_DEFLATED with compresslevel=9")
        else:
            logger.info("No NSP detected (likely NSZ): using ZIP_STORED")

        with zipfile.ZipFile(archive_path, 'w', compression=compression, compresslevel=compresslevel) as archive:
            for f in source_files:
                if os.path.isdir(f):
                    for root, dirs, files in os.walk(f):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, os.path.dirname(f))
                            archive.write(full_path, arcname=rel_path)
                else:
                    archive.write(f, arcname=os.path.basename(f))
                
        # Splitting logic (if file size > split_size)
        file_size = os.path.getsize(archive_path)
        logger.info(f"ZIP Archive created. Total size: {file_size} bytes ({file_size / (1024**2):.1f} MB)")
        
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
                
                part_size = os.path.getsize(part_path)
                logger.info(f"Created part {part_num}: {part_path} ({part_size} bytes)")
                parts.append(part_path)
                part_num += 1
                
        # Remove the original large archive
        os.remove(archive_path)
        return parts
