from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class FilesRegistry(Base):
    __tablename__ = "files_registry"
    
    id = Column(Integer, primary_key=True)
    file_original_name = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String, unique=True, index=True)  # SHA256 or similar
    category = Column(String)  # Base, Update, DLC
    created_at = Column(DateTime, default=datetime.utcnow)
    
    storage_entries = relationship("TelegramStorage", back_populates="file")

class TelegramStorage(Base):
    __tablename__ = "telegram_storage"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files_registry.id"), nullable=False)
    telegram_message_link = Column(String, nullable=False)
    archive_obfuscated_name = Column(String(40), nullable=False)
    is_parted = Column(Boolean, default=False)
    part_number = Column(Integer, nullable=True)
    total_parts = Column(Integer, nullable=True)
    
    file = relationship("FilesRegistry", back_populates="storage_entries")
