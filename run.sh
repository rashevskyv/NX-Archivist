#!/bin/bash

echo "[NX-Archivist] Оновлення коду..."
git pull

# Перевірка наявності venv
if [ ! -d "venv" ]; then
    echo "[NX-Archivist] Створення віртуального оточення..."
    python3 -m venv venv || { echo "[ERROR] Не вдалося створити venv. Встановіть python3-venv: sudo apt install python3-venv"; exit 1; }
fi

echo "[NX-Archivist] Активація venv та встановлення залежностей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[NX-Archivist] Запуск бота..."
python3 nx_archivist/main.py
