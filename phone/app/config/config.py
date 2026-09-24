# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/config/config.py
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from log.log import get_logger
from schemas import PhoneSender

logger = get_logger(__name__)

current_file = Path(__file__).resolve()
PATH_APPLICATION_FOLDER = current_file.parent.parent
PATH_CONFIG_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "config")
PATH_DATA_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "data")


def getApplicationRootFolderFromNameApplicationFolder(
    nameRootApplicationFolder: str, file: str = __file__
) -> str:
    """Определяет корневой каталог приложения"""
    current_dir = os.path.dirname(file)
    parts = current_dir.split(os.sep)

    try:
        index = next(
            i for i, part in enumerate(parts)
            if part.lower() == nameRootApplicationFolder.lower()
        ) + 1
    except StopIteration:
        error_msg = f"⚠️Не найдена директория '{nameRootApplicationFolder}' в пути {current_dir}"
        logger.error(error_msg)
        raise Exception(error_msg)

    application_folder = os.sep.join(parts[:index])

    if application_folder not in sys.path:
        sys.path.insert(0, application_folder)

    return application_folder


class ReloadableConfig(dict):
    """Конфигурация с возможностью перезагрузки"""

    def __init__(self, env_file: str = None):
        current_file = Path(__file__).resolve()
        self.PATH_APPLICATION_FOLDER = current_file.parent.parent
        self._env_file = env_file or os.path.join(
            PATH_CONFIG_FOLDER, "envs", ".env")
        self._last_load_time = None
        self._cache_duration = timedelta(seconds=300)
        self._load_config()

    def _setParameter(self, key, value):
        if isinstance(value,str):
            value=value.strip()
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            match key:
                case "PERIOD_MINUTES_UPDATE_NETWORKINFO" | "PERIOD_MINUTES_UPDATE_CONFIGURATION" | \
                    "PING_TIMEOUT_SECONDS"|'PORT_VPN_SERVER'|'SMTP_PORT'|'PORT_APPLICATION' \
                    'PERIOD_MINUTES_CANARY':
                    value = int(value)
        setattr(self, key, value)
        self[key] = value

    def _read_telegram_chat_ids(self):
        path_chat_ids = os.path.join(
            self.PATH_APPLICATION_FOLDER, "data", "msgprobot_chat_ids.json")
        if not os.path.exists(path_chat_ids):
            error_msg = f"⚠️Файл c chat_id не найден: {path_chat_ids}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

        with open(path_chat_ids, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
        return None
    
    def _read_info_senders(self):
        path_to_senders = os.path.join(
            self.PATH_APPLICATION_FOLDER, "data", "senders.json")
        if not os.path.exists(path_to_senders):
            error_msg = f"⚠️Файл отправителей не найден: {path_to_senders}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

        with open(path_to_senders, "r", encoding="utf-8") as file:
            return json.load(file)
        
    def _read_info_phone_sender(self,data):
        # Используем атрибут self.PHONE_NAME, который должен быть установлен ранее
        phone_name = self.PHONE_NAME
        phones = data["phones"]
        for phone in phones:
            if phone["name"] == phone_name:
                return phone
        error_msg = f"Не найден телефон {phone_name}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def _read_info_email_senders(self,data):
        # Используем атрибут self.PHONE_NAME, который должен быть установлен ранее
        if "emails" in data:return data["emails"]
        else:return []
        
    
    def _load_config(self, force: bool = False) -> None:
        """Загружает конфигурацию из .env файла и устанавливает атрибуты экземпляра"""
        now = datetime.now()

        # Проверяем кэш (если не принудительно)
        if not force and self._last_load_time:
            if now - self._last_load_time < self._cache_duration:
                return  # уже загружено

        if not os.path.exists(self._env_file):
            error_message = f"Файл .env не найден: {self._env_file}"
            logger.critical(error_message)
            raise Exception(error_message)

        # Обновляем переменные окружения
        load_dotenv(self._env_file, override=True)
        env_values = dotenv_values(self._env_file)

        # Устанавливаем все параметры как атрибуты экземпляра
        for key, value in env_values.items():
            # setattr(self, key, value)
            self._setParameter(key, value)

        # Загружаем информацию о телефоне-отправителе
        data=self._read_info_senders()
        sender_data = self._read_info_phone_sender(data)
        self._setParameter('EMAIL_SENDERS',self._read_info_email_senders(data))
        # предполагаем, что PORT_APPLICATION уже установлен
        sender_data["port"] = self.PORT_APPLICATION
        self._setParameter(key, value)
        sender_obj = PhoneSender(**sender_data)

        # Получаем реальный IP и MAC (функция actualeNetworkInfo должна быть импортирована)
        from core.network import actualeNetworkInfo
        ip_address, mac_address = actualeNetworkInfo()
        sender_obj.ip = ip_address
        sender_obj.mac = mac_address
        sender_obj.url = f"http://{sender_obj.ip}:{sender_obj.port}"

        # setattr(self, 'SENDER', sender_obj)
        self._setParameter('SENDER', sender_obj)

        # Преобразуем sims в список номеров без '+'
        # если number None, пропускаем
        phones = [sim.number[1:] for sim in self.SENDER.sims if sim.number]
        logger.info(f"Получены номера телефонов: {phones}")

        # Загружаем chat_ids
        chat_ids_all = self._read_telegram_chat_ids()
        chat_ids = {}  # исправлено: создаём пустой словарь
        for phone in phones:
            if phone in chat_ids_all:
                chat_ids[phone] = chat_ids_all[phone]
            else:
                chat_ids[phone] = "5151092623"

        # setattr(self, 'CHAT_IDS', chat_ids)
        self._setParameter('CHAT_IDS', chat_ids)
        # Обновляем время кэша
        self._last_load_time = now

    def reload(self):
        """Принудительная перезагрузка конфигурации"""
        self._load_config(force=True)

    def getItems(self):
        """Возвращает сам объект для доступа к атрибутам"""
        return self

    def get(self, key, default=None):
        """Получить значение атрибута по ключу"""
        return getattr(self, key, default)


# Создаём глобальный экземпляр
Config = ReloadableConfig()

# Для обратной совместимости

def actualeParameters(pathENVFile=None):
    if pathENVFile:
        Config._env_file = pathENVFile
    Config.reload()
