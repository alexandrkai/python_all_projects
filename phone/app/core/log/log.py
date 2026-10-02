# D:/myprogramms/Python/Phones/PROJECT/REQUIREMENTS/Version3/app/log/log.py
import logging
import logging.handlers
import os
import sys
from datetime import datetime

from config.project_folders import (
    PATH_APPLICATION_FOLDER,
    PATH_CONFIG_FOLDER,
    PATH_LOG_FOLDER,
)
from .critical_error_logger import setup_logger

# Определяем пути


# Создаем директории (без выбрасывания исключений)
print(f"=== LOGGING CONFIGURATION ===")
print(f"✅PROJECT_ROOT: {PATH_APPLICATION_FOLDER}")
print(f"✅PATH_LOG_FOLDER: {PATH_LOG_FOLDER}")
print(f"✅PATH_CONFIG_FOLDER: {PATH_CONFIG_FOLDER}")

try:
    os.makedirs(PATH_LOG_FOLDER, exist_ok=True)
    print(f"✅ Директория логов создана/проверена: {PATH_LOG_FOLDER}")
except Exception as e:
    print(f"❌ Ошибка при создании директории логов: {e}")
    # Используем временную директорию
    PATH_LOG_FOLDER = '/tmp/logs'
    os.makedirs(PATH_LOG_FOLDER, exist_ok=True)
    print(f"⚠️ Использую временную директорию для логов: {PATH_LOG_FOLDER}")

try:
    os.makedirs(PATH_CONFIG_FOLDER, exist_ok=True)
    print(f"✅ Директория конфигов создана/проверена: {PATH_CONFIG_FOLDER}")
except Exception as e:
    print(f"❌ Ошибка при создании директории конфигов: {e}")
    print(f"⚠️ Приложение может работать некорректно без конфигурации")
PHONE_NAME = os.getenv("PHONE_NAME")
# Проверяем наличие .env файла (только предупреждение, не исключение)
env_file = os.path.join(PATH_CONFIG_FOLDER, "envs", f'{PHONE_NAME}.env')
if not os.path.exists(env_file):
    print(f"⚠️ ВНИМАНИЕ: Файл .env не найден в {env_file}")
    print(f"⚠️ Используются значения по умолчанию")

critical_error_logger = setup_logger(PATH_LOG_FOLDER)


class LevelFormatter(logging.Formatter):
    """Кастомный форматтер"""

    def __init__(self):
        super().__init__()
        self.formatters = {
            logging.DEBUG: logging.Formatter(
                '🐛%(asctime)s [DEBUG] %(name)s:%(filename)s:%(lineno)d - %(message)s'
            ),
            logging.INFO: logging.Formatter(
                'ℹ️ %(asctime)s [INFO] %(message)s'
            ),
            logging.WARNING: logging.Formatter(
                '⚠️ %(asctime)s [WARNING] %(name)s:%(filename)s:%(lineno)d - %(message)s'
            ),
            logging.ERROR: logging.Formatter(
                '❌ %(asctime)s [ERROR] %(name)s:%(filename)s:%(lineno)d - %(message)s\n%(exc_info)s'
            ),
            logging.CRITICAL: logging.Formatter(
                '💀🔥 %(asctime)s [CRITICAL] %(name)s:%(filename)s:%(lineno)d - %(message)s\n%(exc_info)s'
            )
        }

    def format(self, record):
        formatter = self.formatters.get(
            record.levelno, self.formatters[logging.INFO])
        return formatter.format(record)


class SmartLogger:
    _instance = None  # Синглтон для гарантии единственной инициализации

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_name='Phone_Service', log_dir=None, environment='development'):
        # Проверяем, был ли уже инициализирован
        if hasattr(self, 'initialized') and self.initialized:
            return

        self.app_name = app_name
        self.log_dir = log_dir if log_dir else PATH_LOG_FOLDER
        self.environment = environment
        self.initialized = True

        # Создаем директорию для логов
        self._ensure_log_directory()

        # Настраиваем логирование
        self._setup_logging()

        print(f"✅ Логгер {app_name} инициализирован в {environment} режиме")
        print(
            f"✅ Логи пишутся в: {os.path.join(self.log_dir, f'{self.app_name.lower()}.log')}")

    def _ensure_log_directory(self):
        """Создание и проверка директории для логов"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            # Проверяем права на запись
            test_file = os.path.join(self.log_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"✅ Директория {self.log_dir} доступна для записи")
        except Exception as e:
            print(f"❌ Ошибка доступа к директории {self.log_dir}: {e}")
            # Пробуем использовать /tmp
            self.log_dir = '/tmp/logs'
            os.makedirs(self.log_dir, exist_ok=True)
            print(f"⚠️ Использую временную директорию: {self.log_dir}")

    def _setup_logging(self):
        """Настройка логирования"""
        # Получаем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Очищаем существующие обработчики
        root_logger.handlers.clear()

        # Основной файловый обработчик
        log_file = os.path.join(self.log_dir, f'{self.app_name.lower()}.log')
        print(f"✅Основной лог-файл: {os.path.abspath(log_file)}")

        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(LevelFormatter())
            root_logger.addHandler(file_handler)
            print(f"✅ Файловый обработчик добавлен")
        except Exception as e:
            print(f"❌ Ошибка при создании файлового обработчика: {e}")
            print(f"⚠️ Будут использоваться только консольные логи")

        # Консольный обработчик (всегда добавляем)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            logging.DEBUG if self.environment == 'development' else logging.INFO)
        # Используем тот же форматтер для консоли
        console_handler.setFormatter(LevelFormatter())
        root_logger.addHandler(console_handler)

        # Логируем начало сессии
        logging.info(f"Лог-сессия начата: {datetime.now()}")  # noqa: DTZ005
        logging.info(f"Окружение: {self.environment}")

    def get_logger(self, name=None):
        """Получить логгер"""
        if name:
            return logging.getLogger(f'{self.app_name}.{name}')
        return logging.getLogger(self.app_name)


# Создаем глобальный экземпляр
_log_manager = None


def init_logging(app_name='phone', log_dir=None, environment='development'):
    """Инициализация логирования (вызовите это первой в main)"""
    global _log_manager
    _log_manager = SmartLogger(app_name, log_dir, environment)
    return _log_manager


def get_logger(name=None):
    """Получить логгер (после init_logging)"""
    global _log_manager
    if _log_manager is None:
        # Автоматическая инициализация с настройками по умолчанию
        _log_manager = SmartLogger()
    return _log_manager.get_logger(name)


# Автоматическая инициализация при импорте
init_logging()

# Создаем глобальный логгер
logger = get_logger(__name__)
