# NX-Archivist Project Plan

## 🎯 Objective
Create a comprehensive Telegram-based "Pirate Cloud" ecosystem for Nintendo Switch games with robust deduplication and secure storage.

## 🏗 Architecture Modules

- [x] **Bot Interface (aiogram 3.x)**
    - [x] User interaction (Search, Select Release)
    - [x] Status UI (`/status` command & persistent button)
    - [ ] Delivery of final links (Refining format)
- [x] **Torrent Engine (libtorrent)**
    - [x] Magnet/File handling
    - [x] Selective Downloading (Deduplication check)
- [x] **The Archivist**
    - [x] 7z Packing & Splitting (1.9GB / 3.9GB)
    - [x] Obfuscated naming (40-char random)
    - [x] **Encryption**: AES-256 (Password from config)
- [x] **Categorizer**
    - [x] Regex logic for Base, Update, DLC
    - [x] **Special Logic**: Group DLCs > 5 into a single "DLC Pack"
- [x] **Uploader (Telethon)**
    - [x] MTProto uploads to Storage Channel
    - [x] Robust entity resolution
- [x] **Database (SQLAlchemy + SQLite)**
    - [x] `FilesRegistry` & `TelegramStorage` models
    - [x] Mapping real files to Telegram links

## 🧠 Database Logic (Workflow)

1.  [x] Parse Torrent Metadata.
2.  [x] For each file (or DLC group), check DB.
3.  [x] If exists -> Skip download, retrieve Link.
4.  [/] If not exists -> Download -> Archive -> Upload -> Save to DB -> Return Link.

## 🛠 Configuration Schema (.env)
- [x] `BOT_TOKEN`, `API_ID`, `API_HASH`
- [x] `RUTRACKER_USERNAME`, `RUTRACKER_PASSWORD`
- [x] `STORAGE_CHANNEL_ID`
- [x] `IS_TELEGRAM_PREMIUM`
- [ ] `ENCRYPTION_PASSWORD` (To be added)

## 📅 Step-by-Step Implementation Status

### Phase 1: Core Infrastructure [COMPLETED]
- [x] Project structure setup
- [x] Database models
- [x] Basic RuTracker search & Torrent download

### Phase 2: Parallelism & Status [COMPLETED]
- [x] Background task manager
- [x] Real-time status reporting (Speed, ETA, Progress)
- [x] Multi-threaded archiving
- [x] **Detailed Console Logging**: Real-time logs for downloads, archiving, and uploads.

### Phase 3: Refinement & Security [COMPLETED]
- [x] **AES-256 Encryption** in Archivist
- [x] **DLC Grouping** logic (if > 5 DLCs)
- [x] **Refined Reporting**:
    - [x] Remove captions from uploads
    - [x] Send direct links + filenames to user
    - [x] "Part X" naming only for split files
- [x] **Cleanup**: Ensure `DELETE_AFTER_UPLOAD` works perfectly

### Phase 4: Production Readiness [PENDING]
- [ ] Dockerization
- [ ] Error handling edge cases (RuTracker downtime, etc.)
- [ ] User documentation (README updates)
