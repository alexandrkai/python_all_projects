#!/usr/bin/env bash
set -euo pipefail

# --- НАСТРОЙКИ ---
REMOTE_USER="kai"
REMOTE_HOST="192.168.1.50"
REMOTE_PORT="8022"
REMOTE_LOG_PATH="/data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api/app/logs"
LOCAL_BACKUP_DIR="/mnt/d/myprogramms/Python/phone/logs"

# Создаём локальную папку, если нет
mkdir -p "$LOCAL_BACKUP_DIR"

# Синхронизируем: скачиваем только новые/изменённые файлы, сохраняем даты
rsync -av --delete \
  -e "ssh -p $REMOTE_PORT" \
  "$REMOTE_USER@$REMOTE_HOST:$REMOTE_LOG_PATH/" \
  "$LOCAL_BACKUP_DIR/"

echo "Логи успешно скачаны в $LOCAL_BACKUP_DIR"
