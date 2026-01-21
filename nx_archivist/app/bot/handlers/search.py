from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from app.services.rutracker import RuTrackerService
from app.core.torrent import TorrentManager
from app.core.categorizer import Categorizer
from app.core.archivist import Archivist
from app.services.uploader import Uploader
from app.db.base import async_session
from app.db.models import FilesRegistry, TelegramStorage
from app.core.config import config
import os
import logging

search_router = Router()
rutracker = RuTrackerService()
torrent_manager = TorrentManager()
uploader = Uploader()

@search_router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привіт! Я NX-Archivist. Надішли мені назву гри для пошуку на RuTracker.")

@search_router.message(F.text)
async def handle_search(message: Message):
    query = message.text
    await message.answer(f"Шукаю '{query}' на RuTracker...")
    
    results = await rutracker.search(query)
    
    if not results:
        await message.answer("Нічого не знайдено.")
        return
        
    for res in results[:5]: # Show top 5
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вибрати цей реліз", callback_data=f"select_{res['id']}")]
        ])
        await message.answer(
            f"📦 {res['title']}\n"
            f"💾 Розмір: {res['size']}\n"
            f"🌱 Сідів: {res['seeds']}",
            reply_markup=kb
        )

@search_router.callback_query(F.data.startswith("select_"))
async def handle_select_release(callback: CallbackQuery):
    topic_id = callback.data.split("_")[1]
    await callback.message.edit_text("Отримую метадані торрента та перевіряю кеш...")
    
    torrent_data = await rutracker.get_torrent_file(topic_id)
    if not torrent_data:
        await callback.message.answer("Не вдалося отримати торрент-файл.")
        return
        
    handle = await torrent_manager.add_torrent(torrent_data, config.DOWNLOAD_DIR)
    files_status = await torrent_manager.check_deduplication(handle)
    
    response = "📂 **Список файлів у релізі:**\n\n"
    to_download = []
    
    for f in files_status:
        status_icon = "✅" if f["exists"] else "📥"
        response += f"{status_icon} `{f['name']}` ({f['size'] / (1024**2):.1f} MB)\n"
        if f["exists"]:
            response += f"   🔗 [Посилання]({f['link']})\n"
        else:
            to_download.append(f["index"])
            
    if not to_download:
        response += "\n✨ Усі файли вже є в базі! Завантаження не потрібне."
        await callback.message.answer(response, parse_mode="Markdown")
    else:
        response += f"\n🚀 Потрібно завантажити {len(to_download)} нових файлів."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Почати завантаження", callback_data=f"download_{topic_id}")]
        ])
        await callback.message.answer(response, parse_mode="Markdown", reply_markup=kb)
    
    await callback.answer()

@search_router.callback_query(F.data.startswith("download_"))
async def handle_download(callback: CallbackQuery):
    topic_id = callback.data.split("_")[1]
    await callback.message.edit_text("⏳ Починаю завантаження та обробку релізу...")
    
    # 1. Get torrent and handle
    torrent_data = await rutracker.get_torrent_file(topic_id)
    handle = await torrent_manager.add_torrent(torrent_data, config.DOWNLOAD_DIR)
    
    # 2. Check which files to download
    files_status = await torrent_manager.check_deduplication(handle)
    to_download_indices = [f["index"] for f in files_status if not f["exists"]]
    
    if not to_download_indices:
        await callback.message.answer("Всі файли вже завантажені.")
        return
        
    # 3. Download
    await torrent_manager.start_selective_download(handle, to_download_indices)
    await callback.message.answer("✅ Завантаження завершено. Починаю архівацію...")
    
    # 4. Categorize and Process
    downloaded_files = [torrent_manager.get_file_path(handle, i) for i in to_download_indices]
    groups = Categorizer.group_dlcs(downloaded_files)
    
    final_links = []
    
    async with async_session() as session:
        for cat, files in groups.items():
            if not files:
                continue
                
            # If DLCs > 5, they are already grouped in 'files' list
            # We pack each category (or DLC pack) separately
            archive_name = Archivist.generate_obfuscated_name()
            parts = Archivist.pack_and_split(files, config.DOWNLOAD_DIR, archive_name)
            
            await callback.message.answer(f"📦 Завантажую {cat} ({len(parts)} частин)...")
            
            # 5. Upload and Save to DB
            for i, part in enumerate(parts):
                link = await uploader.upload_file(part, caption=f"{cat} - Part {i+1}")
                
                # Register in DB (simplified for prototype)
                # In real app, we'd link multiple parts to one FilesRegistry entry
                for original_file in files:
                    new_file = FilesRegistry(
                        file_original_name=os.path.basename(original_file),
                        file_size=os.path.getsize(original_file),
                        category=cat
                    )
                    session.add(new_file)
                    await session.flush()
                    
                    new_storage = TelegramStorage(
                        file_id=new_file.id,
                        telegram_message_link=link,
                        archive_obfuscated_name=archive_name,
                        is_parted=len(parts) > 1,
                        part_number=i+1,
                        total_parts=len(parts)
                    )
                    session.add(new_storage)
                
                if i == 0: # Store first part link for display
                    final_links.append(f"🔹 **{cat}**: [Посилання]({link})")
                    
            await session.commit()
            
    response = "✨ **Обробка завершена!**\n\n" + "\n".join(final_links)
    await callback.message.answer(response, parse_mode="Markdown")
