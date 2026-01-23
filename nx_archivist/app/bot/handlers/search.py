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
import shutil

search_router = Router()
rutracker = RuTrackerService()
torrent_manager = TorrentManager()
uploader = Uploader()

@search_router.message(Command("start"))
async def cmd_start(message: Message):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статус")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Привіт! Я NX-Archivist. Надішли мені назву гри для пошуку на RuTracker.",
        reply_markup=kb
    )

@search_router.message(F.text, ~F.text.startswith("/"))
async def handle_search(message: Message):
    query = message.text
    
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    kb_status = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статус")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(f"Шукаю '{query}' на RuTracker...", reply_markup=kb_status)
    
    results = await rutracker.search(query)
    
    if not results:
        await message.answer("Нічого не знайдено.")
        return
        
    for res in results[:15]: # Show top 15
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
    to_download_indices = []
    
    for f in files_status:
        status_icon = "✅" if f["exists"] else "📥"
        if f.get("is_folder"):
            response += f"{status_icon} 📁 `{f['name']}` ({len(f['indices'])} файлів, {f['size'] / (1024**2):.1f} MB)\n"
        else:
            response += f"{status_icon} `{f['name']}` ({f['size'] / (1024**2):.1f} MB)\n"
            
        if f["exists"]:
            response += f"   🔗 [Посилання]({f['link']})\n"
        else:
            if f.get("is_folder"):
                to_download_indices.extend(f["indices"])
            else:
                to_download_indices.append(f["index"])
            
    if not to_download_indices:
        response += "\n✨ Усі файли вже є в базі! Завантаження не потрібне."
        await callback.message.answer(response, parse_mode="Markdown")
    else:
        response += f"\n🚀 Потрібно завантажити нові файли."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Почати завантаження", callback_data=f"download_{topic_id}")]
        ])
        await callback.message.answer(response, parse_mode="Markdown", reply_markup=kb)
    
    await callback.answer()

@search_router.callback_query(F.data.startswith("download_"))
async def handle_download(callback: CallbackQuery):
    topic_id = callback.data.split("_")[1]
    
    # 1. Get torrent info to get a name for the task
    torrent_data = await rutracker.get_torrent_file(topic_id)
    if not torrent_data:
        await callback.answer("Не вдалося отримати торрент-файл.", show_alert=True)
        return
        
    import libtorrent as lt
    info = lt.torrent_info(lt.bdecode(torrent_data))
    task_name = info.name()
    
    # 2. Create task
    from app.core.tasks import task_manager
    task_id = task_manager.create_task(task_name)
    
    # 3. Start background task
    import asyncio
    asyncio.create_task(process_download_task(task_id, topic_id, callback.message.chat.id))
    
    await callback.message.answer(
        f"🚀 Завдання додано в чергу!\n"
        f"📦 **{task_name}**\n"
        f"🆔 ID: `{task_id}`\n\n"
        f"Використовуйте /status для відстеження."
    )
    await callback.answer()

async def process_download_task(task_id: str, topic_id: str, chat_id: int):
    from app.core.tasks import task_manager, TaskStatus
    import main as main_module
    from main import logger
    
    bot = main_module.bot_instance

    try:
        # 1. Get torrent and handle
        torrent_data = await rutracker.get_torrent_file(topic_id)
        handle = await torrent_manager.add_torrent(torrent_data, config.DOWNLOAD_DIR)
        
        # 2. Check which files to download
        files_status = await torrent_manager.check_deduplication(handle)
        
        # Collect all indices to download
        all_to_download = []
        for f in files_status:
            if not f["exists"]:
                if f.get("is_folder"):
                    all_to_download.extend(f["indices"])
                else:
                    all_to_download.append(f["index"])
        
        if not all_to_download:
            task_manager.update_task(task_id, status=TaskStatus.COMPLETED, progress=100.0)
            if bot: await bot.send_message(chat_id, f"✅ Завдання `{task_id}` завершено: всі файли вже в базі.")
            return
            
        # 3. Download
        await torrent_manager.start_selective_download(handle, all_to_download, task_id=task_id)
        
        # 4. Packing
        task_manager.update_task(task_id, status=TaskStatus.PACKING, progress=0.0)
        final_links = []
        
        async with async_session() as session:
            for entity in files_status:
                if entity["exists"]:
                    continue
                    
                source_paths = []
                if entity.get("is_folder"):
                    source_paths = [os.path.join(config.DOWNLOAD_DIR, entity["name"])]
                    cat = "Folder"
                    entity_hash = entity["hash"]
                    original_name = entity["name"]
                else:
                    source_paths = [torrent_manager.get_file_path(handle, entity["index"])]
                    cat = Categorizer.categorize(source_paths[0])
                    entity_hash = None
                    original_name = os.path.basename(source_paths[0])

                archive_name = Archivist.generate_obfuscated_name()
                parts = Archivist.pack_and_split(source_paths, config.DOWNLOAD_DIR, archive_name)
                
                # 5. Upload
                for i, part in enumerate(parts):
                    link = await uploader.upload_file(part, caption=f"{original_name} - Part {i+1}", task_id=task_id)
                    
                    new_file = FilesRegistry(
                        file_original_name=original_name,
                        file_size=entity["size"],
                        file_hash=entity_hash,
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
                    
                    if i == 0:
                        final_links.append(f"🔹 **{original_name}**: [Посилання]({link})")
                
                # Cleanup
                if config.DELETE_AFTER_UPLOAD:
                    for path in source_paths:
                        try:
                            if os.path.isdir(path): shutil.rmtree(path)
                            else: os.remove(path)
                        except Exception as e: logger.error(f"Cleanup error: {e}")
            
            await session.commit()
            
        task_manager.update_task(task_id, status=TaskStatus.COMPLETED, progress=100.0)
        response = f"✨ **Завдання `{task_id}` завершено!**\n\n" + "\n".join(final_links)
        if bot: await bot.send_message(chat_id, response, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"Error in task {task_id}: {e}")
        task_manager.update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        if bot: await bot.send_message(chat_id, f"❌ Помилка у завданні `{task_id}`: {e}")

@search_router.message(Command("status"))
@search_router.message(F.text == "📊 Статус")
async def cmd_status(message: Message):
    from app.core.tasks import task_manager
    tasks = task_manager.get_active_tasks()
    
    if not tasks:
        await message.answer("Немає активних завдань.")
        return
        
    response = "📊 **Активні завдання:**\n\n"
    for t in tasks:
        progress_bar = "▓" * int(t.progress / 10) + "░" * (10 - int(t.progress / 10))
        speed_kb = t.speed / 1024
        eta_min = t.eta / 60
        
        response += (
            f"📦 **{t.name}**\n"
            f"🆔 `{t.id}` | {t.status.value.upper()}\n"
            f"[{progress_bar}] {t.progress:.1f}%\n"
            f"⚡ Швидкість: {speed_kb:.1f} KB/s\n"
            f"⏳ Залишилось: {eta_min:.1f} хв\n\n"
        )
    
    await message.answer(response, parse_mode="Markdown")

@search_router.callback_query(F.data == "check_status")
async def handle_check_status(callback: CallbackQuery):
    # This is kept for backward compatibility if any old messages are still around
    await cmd_status(callback.message)
    await callback.answer()
