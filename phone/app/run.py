#!/data/data/com.termux/files/usr/bin/python3
# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/run.py
import atexit
import os
import signal
import subprocess
import sys
import time

from config.config import Config
from log.log import get_logger

logger=get_logger(__name__)

# Добавляем текущую директорию в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Вспомогательные функции ---
def acquire_wakelock():
    """Захватывает wakelock для предотвращения сна CPU"""
    try:
        subprocess.run(["termux-wake-lock"], check=True, capture_output=True)
        logger.info(f"❌[{time.ctime()}] INFO: Wakelock acquired via termux-api")
    except Exception as e:
        logger.error(f"[{time.ctime()}] ERROR: Failed to acquire wakelock: {e}")

def release_wakelock():
    """Освобождает wakelock"""
    try:
        subprocess.run(["termux-wake-unlock"], check=True, capture_output=True)
        logger.info(f"❌[{time.ctime()}] INFO: Wakelock released")
    except Exception as e:
        logger.error(f"[{time.ctime()}] ERROR: Failed to release wakelock: {e}")

def handle_exit(signum=None, frame=None):
    """Обработчик выхода"""
    logger.info(f"❌[{time.ctime()}] INFO: Shutting down service...")
    release_wakelock()
    sys.exit(0)

# --- Настройка ---
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
atexit.register(release_wakelock)

# --- Основной блок ---
if __name__ == "__main__":
    logger.info(f"❌[{time.ctime()}] INFO: Starting API Service...")
    acquire_wakelock()

    # Сохраняем PID (опционально, полезно для kill)
    with open(os.path.expanduser("~/api.pid"), "w") as f:
        f.write(str(os.getpid()))

    try:
        import uvicorn
        # Импортируем приложение здесь, чтобы убедиться, что нет ошибок импорта до запуска сервера
        from main import app

        logger.info(f"❌[{time.ctime()}] INFO: Uvicorn starting on http://0.0.0.0:8000")
        logger.info(f"❌[{time.ctime()}] INFO: Logging to standard output (handled by nohup)")

        # ЗАПУСК СЕРВЕРА
        # reload=False - обязательно для nohup, чтобы не было проблем с процессами
        # access_log=False - можно включить для дебага, но это создает много логов
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=int(Config.PORT_APPLICATION), 
            reload=False,  # <--- ВАЖНО: отключаем перезагрузку
            log_level="info"
        )

    except Exception as e:
        logger.critical(f"💀[{time.ctime()}] CRITICAL: Uvicorn crashed: {e}")
        # Ждем немного, чтобы успеть прочитать ошибку перед выходом (если не в фоне)
        time.sleep(1)
        handle_exit()

# nohup python run.py > api.log 2>&1 &